"""Pure merchant automation primitives used by the Durin MCP.

This module has no MCP, network, PayPal, or model dependency. Keeping the
preflight engine pure makes the proposal reproducible and independently testable.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


MAX_INVOICES = 500
MAX_FIELD_LENGTH = 256
MAX_DECIMAL_DIGITS = 40
INVOICE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,99}$")


def _text(value: Any, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if len(value) > MAX_FIELD_LENGTH:
        raise ValueError(f"{field} exceeds the length limit")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    return value


def parse_amount(value: Any, field: str = "amount") -> Decimal:
    raw = _text(value, field)
    if len(raw) > MAX_DECIMAL_DIGITS or not re.fullmatch(r"\d+(?:\.\d{1,4})?", raw):
        raise ValueError(f"{field} must be a positive decimal amount")
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{field} is not a valid decimal amount") from exc
    if parsed <= 0:
        raise ValueError(f"{field} must be greater than zero")
    return parsed


def format_money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def invoice_identity(invoice: dict[str, Any]) -> tuple[str, str, str, str]:
    supplier = _text(invoice.get("supplier"), "supplier").casefold()
    number = _text(invoice.get("invoiceNumber"), "invoiceNumber").casefold()
    currency = _text(invoice.get("currency", "USD"), "currency").upper()
    amount = format_money(parse_amount(invoice.get("amount")))
    return supplier, number, currency, amount


def find_duplicates(invoices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return duplicate groups without deciding intent or fraud."""
    if not isinstance(invoices, list) or len(invoices) > MAX_INVOICES:
        raise ValueError("invoices must be a bounded array")
    groups: dict[tuple[str, str, str, str], list[str]] = {}
    for index, invoice in enumerate(invoices):
        if not isinstance(invoice, dict):
            raise ValueError(f"invoice {index} must be an object")
        identity = invoice_identity(invoice)
        invoice_id = _text(invoice.get("invoiceId", f"row-{index}"), "invoiceId")
        groups.setdefault(identity, []).append(invoice_id)
    return [
        {"identity": list(identity), "invoiceIds": ids}
        for identity, ids in groups.items()
        if len(ids) > 1
    ]


def _distance_one_or_two(left: str, right: str) -> int | None:
    if len(left) != len(right):
        return None
    distance = sum(a != b for a, b in zip(left.casefold(), right.casefold()))
    return distance if 1 <= distance <= 2 else None


def prepare_proposal(invoices: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    """Apply a validated merchant policy and return a review-only proposal."""
    if not isinstance(invoices, list) or len(invoices) > MAX_INVOICES:
        raise ValueError("invoices must be a bounded array")
    configured_recipients = policy.get("approvedRecipients")
    if not isinstance(configured_recipients, list) or not configured_recipients:
        raise ValueError("approvedRecipients must be a non-empty list")
    approved = {str(value).casefold() for value in configured_recipients}
    base_currency = _text(policy.get("baseCurrency", "USD"), "baseCurrency").upper()
    max_payment = Decimal(str(policy["maxAmountPerPayment"]))
    max_batch = Decimal(str(policy["maxAmountPerBatch"]))
    approval_threshold = Decimal(str(policy["approvalRequiredAbove"]))
    seen: set[tuple[str, str, str, str]] = set()
    accepted: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    total = Decimal("0")
    for index, invoice in enumerate(invoices):
        if not isinstance(invoice, dict):
            raise ValueError(f"invoice {index} must be an object")
        invoice_id = _text(invoice.get("invoiceId"), "invoiceId")
        if not INVOICE_ID_RE.fullmatch(invoice_id):
            raise ValueError("invoiceId has an invalid format")
        recipient = _text(invoice.get("recipient"), "recipient")
        amount = parse_amount(invoice.get("amount"))
        currency = _text(invoice.get("currency", policy.get("baseCurrency", "USD")), "currency").upper()
        supplier = _text(invoice.get("supplier"), "supplier")
        number = _text(invoice.get("invoiceNumber"), "invoiceNumber")
        identity = (supplier.casefold(), number.casefold(), currency, format_money(amount))
        reasons: list[str] = []
        if currency != base_currency:
            reasons.append("CURRENCY_NOT_SUPPORTED")
        if invoice.get("requiresReview") is True:
            reasons.append("REQUIRES_SOURCE_REVIEW")
        if identity in seen:
            reasons.append("POSSIBLE_DUPLICATE")
        seen.add(identity)
        if approved and recipient.casefold() not in approved:
            candidates = [
                {"recipient": candidate, "distance": distance}
                for candidate in configured_recipients
                if (distance := _distance_one_or_two(recipient, candidate)) is not None
            ]
            reasons.append("POSSIBLE_TYPO" if len(candidates) == 1 else "RECIPIENT_NOT_APPROVED")
        if amount > max_payment:
            reasons.append("EXCEEDS_PER_PAYMENT_LIMIT")
        if total + amount > max_batch:
            reasons.append("EXCEEDS_BATCH_LIMIT")
        item = {
            "invoiceId": invoice_id,
            "supplier": supplier,
            "invoiceNumber": number,
            "recipient": recipient,
            "amount": format_money(amount),
            "currency": currency,
        }
        if reasons:
            excluded.append({**item, "action": "EXCLUDED", "reasons": reasons})
        else:
            total += amount
            accepted.append({
                **item,
                "action": "READY_FOR_REVIEW",
                "approvalRequired": amount >= approval_threshold,
            })
    return {
        "accepted": accepted,
        "excluded": excluded,
        "totalAmount": format_money(total),
        "currency": policy.get("baseCurrency", "USD"),
        "execution": "NO_PAYMENT_SUBMITTED",
        "humanApprovalRequired": True,
    }
