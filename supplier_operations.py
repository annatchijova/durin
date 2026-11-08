"""Deterministic supplier operations engine adapted from Durin's source workflow.

The engine knows about merchant obligations and provider operations, but not
about a particular payment network. PayPal is an adapter concern. This keeps
duplicate detection, conflicts, preflight, and reporting reusable.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from automation import format_money, parse_amount


MAX_ITEMS = 500
PRICE_ALERT_PERCENT = Decimal("15")
PENDING_OPERATION_STATES = {"PENDING", "PROCESSING", "ON_HOLD", "UNKNOWN"}


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    if len(value) > 256:
        raise ValueError(f"{field} exceeds the length limit")
    return value.strip()


def _currency(value: Any) -> str:
    result = _required_text(value, "currency").upper()
    if len(result) != 3 or not result.isalpha():
        raise ValueError("currency must be a three-letter code")
    return result


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(_required_text(value, field))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def _observed_date(value: Any) -> date:
    text = _required_text(value, "observed_at")
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError as exc:
        raise ValueError("observed_at must be an ISO timestamp") from exc


def _identity(invoice: dict[str, Any]) -> tuple[str, str, str, str]:
    supplier = _required_text(invoice.get("supplier"), "supplier").casefold()
    number = _required_text(invoice.get("invoiceNumber"), "invoiceNumber").casefold()
    currency = _currency(invoice.get("currency"))
    amount = format_money(parse_amount(invoice.get("amount")))
    return supplier, number, currency, amount


def _typo_candidate(value: str, approved: list[str]) -> dict[str, Any] | None:
    candidates = []
    for item in approved:
        if len(item) != len(value):
            continue
        distance = sum(a != b for a, b in zip(item.casefold(), value.casefold()))
        if 1 <= distance <= 2:
            candidates.append({"recipient": item, "distance": distance})
    return candidates[0] if len(candidates) == 1 else None


def _history_average(history: Any, currency: str) -> Decimal | None:
    if not isinstance(history, list) or not history:
        return None
    values = []
    for item in history:
        if not isinstance(item, dict):
            raise ValueError("history entries must be objects")
        if _currency(item.get("currency", currency)) != currency:
            continue
        values.append(parse_amount(item.get("amount"), "history.amount"))
    return sum(values, Decimal("0")) / len(values) if values else None


def _operation_for(invoice: dict[str, Any], operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    invoice_id = _required_text(invoice.get("invoiceId"), "invoiceId")
    invoice_number = _required_text(invoice.get("invoiceNumber"), "invoiceNumber").casefold()
    matches = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("operations entries must be objects")
        references = {
            str(operation.get("invoiceId", "")),
            str(operation.get("invoiceNumber", "")).casefold(),
        }
        if invoice_id in references or invoice_number in references:
            matches.append(operation)
    return matches


def preflight_supplier(
    invoice: dict[str, Any], *, policy: dict[str, Any], operations: list[dict[str, Any]],
    seen: set[tuple[str, str, str, str]], observed_date: date | None = None,
) -> dict[str, Any]:
    """Evaluate one supplier obligation without submitting a payment."""
    invoice_id = _required_text(invoice.get("invoiceId"), "invoiceId")
    supplier = _required_text(invoice.get("supplier"), "supplier")
    invoice_number = _required_text(invoice.get("invoiceNumber"), "invoiceNumber")
    recipient = _required_text(invoice.get("recipient"), "recipient")
    amount = parse_amount(invoice.get("amount"))
    currency = _currency(invoice.get("currency"))
    identity = _identity(invoice)
    reasons: list[str] = []
    checks: list[dict[str, str]] = []

    duplicate = identity in seen
    seen.add(identity)
    checks.append({"key": "unique", "status": "fail" if duplicate else "pass", "detail": "duplicate identity" if duplicate else "no duplicate in batch"})
    if duplicate:
        reasons.append("POSSIBLE_DUPLICATE")

    approved = [str(item) for item in policy.get("approvedRecipients", [])]
    recipient_approved = not approved or recipient.casefold() in {item.casefold() for item in approved}
    typo = None if recipient_approved else _typo_candidate(recipient, approved)
    checks.append({"key": "recipient", "status": "pass" if recipient_approved else "fail", "detail": "approved" if recipient_approved else "not approved"})
    if not recipient_approved:
        reasons.append("POSSIBLE_TYPO" if typo else "RECIPIENT_NOT_APPROVED")

    max_amount = parse_amount(policy["maxAmountPerPayment"], "maxAmountPerPayment")
    over_limit = amount > max_amount
    checks.append({"key": "limit", "status": "fail" if over_limit else "pass", "detail": f"{format_money(amount)} {'>' if over_limit else '<='} {format_money(max_amount)}"})
    if over_limit:
        reasons.append("EXCEEDS_PER_PAYMENT_LIMIT")

    average = _history_average(invoice.get("history", []), currency)
    price_change = None
    if average and average > 0:
        price_change = ((amount - average) * Decimal("100") / average).quantize(Decimal("0.01"))
    price_alert = price_change is not None and price_change > PRICE_ALERT_PERCENT
    checks.append({"key": "price", "status": "alert" if price_alert else "pass", "detail": "no comparable history" if average is None else f"change={price_change}%"})
    if price_alert:
        reasons.append("PRICE_ALERT")

    matches = _operation_for(invoice, operations)
    recognized_amount: str | None = None
    if len(matches) > 1:
        reasons.append("AMBIGUOUS_OPERATION")
        operation_state = "AMBIGUOUS"
    elif not matches:
        operation_state = "UNMATCHED"
    else:
        operation = matches[0]
        op_amount = parse_amount(operation.get("amount"), "operation.amount")
        op_currency = _currency(operation.get("currency"))
        operation_status = str(operation.get("status", "UNKNOWN")).upper()
        if op_currency != currency or op_amount > amount:
            reasons.append("OPERATION_MISMATCH")
            operation_state = "MISMATCHED"
        elif op_amount < amount:
            reasons.append("PARTIAL_OPERATION")
            operation_state = "PARTIALLY_MATCHED"
            recognized_amount = format_money(op_amount)
        else:
            operation_state = operation_status
            if operation_status in PENDING_OPERATION_STATES:
                reasons.append("PENDING_OPERATION")

    due_date = None
    if invoice.get("dueDate") is not None:
        due_date = _date(invoice.get("dueDate"), "dueDate")
    overdue = bool(due_date and observed_date and due_date < observed_date and operation_state not in {"SUCCESS", "COMPLETED", "PAID"})
    checks.append({
        "key": "due_date",
        "status": "alert" if overdue else "pass",
        "detail": "overdue" if overdue else (f"due {due_date.isoformat()}" if due_date else "no due date"),
    })
    if overdue:
        reasons.append("OVERDUE")

    item = {
        "invoiceId": invoice_id,
        "supplier": supplier,
        "invoiceNumber": invoice_number,
        "recipient": recipient,
        "amount": format_money(amount),
        "currency": currency,
        "operationState": operation_state,
        "reasons": reasons,
        "checks": checks,
        "status": "EXCLUDED" if reasons else "READY_FOR_REVIEW",
    }
    if due_date is not None:
        item["dueDate"] = due_date.isoformat()
    if typo:
        item["typoSuggestion"] = typo
    if average is not None:
        item["historyAverage"] = format_money(average)
        item["priceChangePercent"] = str(price_change)
    if matches:
        item["operationIds"] = [str(operation.get("operationId", "")) for operation in matches]
    if recognized_amount is not None:
        item["recognizedAmount"] = recognized_amount
    return item


def analyze_supplier_batch(
    invoices: list[dict[str, Any]], operations: list[dict[str, Any]], *, policy: dict[str, Any],
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Return preflight rows and exact metrics for a supplier batch."""
    if not isinstance(invoices, list) or len(invoices) > MAX_ITEMS:
        raise ValueError("invoices must be a bounded array")
    if not isinstance(operations, list) or len(operations) > MAX_ITEMS:
        raise ValueError("operations must be a bounded array")
    seen: set[tuple[str, str, str, str]] = set()
    observed_date = _observed_date(observed_at) if observed_at is not None else None
    rows = [
        preflight_supplier(invoice, policy=policy, operations=operations, seen=seen, observed_date=observed_date)
        for invoice in invoices
    ]
    reason_counts = Counter(reason for row in rows for reason in row["reasons"])
    amounts = defaultdict(lambda: Decimal("0"))
    for row in rows:
        if row["status"] == "READY_FOR_REVIEW":
            amounts[row["currency"]] += Decimal(row["amount"])
    operation_counts = Counter(row["operationState"] for row in rows)
    return {
        "rows": rows,
        "metrics": {
            "invoiceCount": len(rows),
            "readyCount": sum(row["status"] == "READY_FOR_REVIEW" for row in rows),
            "excludedCount": sum(row["status"] == "EXCLUDED" for row in rows),
            "reasonCounts": dict(sorted(reason_counts.items())),
            "operationStateCounts": dict(sorted(operation_counts.items())),
            "readyAmountsByCurrency": {currency: format_money(amount) for currency, amount in sorted(amounts.items())},
        },
        "execution": "NO_PAYMENT_SUBMITTED",
        "humanApprovalRequired": True,
    }
