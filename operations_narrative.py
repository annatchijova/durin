"""Business-language explanations for deterministic supplier results."""

from __future__ import annotations

from collections import Counter
from typing import Any


REASON_TEXT = {
    "POSSIBLE_DUPLICATE": "This invoice repeats an existing supplier invoice identity.",
    "POSSIBLE_TYPO": "The payment recipient is very similar to an approved recipient but is not identical.",
    "RECIPIENT_NOT_APPROVED": "The recipient is not in the merchant's approved recipient list.",
    "PRICE_ALERT": "The amount is above the supplier's recorded price history threshold.",
    "EXCEEDS_PER_PAYMENT_LIMIT": "The amount exceeds the merchant's per-payment limit.",
    "EXCEEDS_BATCH_LIMIT": "The batch limit would be exceeded.",
    "AMBIGUOUS_OPERATION": "More than one provider operation matches this obligation.",
    "OPERATION_MISMATCH": "A provider operation was found, but its amount or currency does not match.",
    "PARTIAL_OPERATION": "A provider operation covers only part of the obligation; the remaining amount is unresolved.",
    "PENDING_OPERATION": "A provider operation exists but its provider status is not final.",
    "CONFLICTING_SUPPLIER_IDENTITY": "The same invoice number appears under different supplier identities.",
    "CONFLICTING_INVOICE_FACTS": "The same supplier and invoice number have conflicting amount or currency facts.",
    "OVERDUE": "The obligation passed its due date without a recognized successful settlement.",
}


def explain_row(row: dict[str, Any]) -> dict[str, Any]:
    """Narrate a row without changing its deterministic status or reasons."""
    reasons = list(row.get("reasons", []))
    if not reasons and row.get("operationState") == "SUCCESS":
        text = f"{row['supplier']} invoice {row['invoiceNumber']} matches a successful provider operation for {row['amount']} {row['currency']}."
    elif not reasons:
        text = f"{row['supplier']} invoice {row['invoiceNumber']} is ready for review; no provider operation has been matched yet."
    else:
        explanations = [REASON_TEXT.get(reason, f"Unclassified exception: {reason}.") for reason in reasons]
        text = f"{row['supplier']} invoice {row['invoiceNumber']} is not ready: " + " ".join(explanations)
    if row.get("operationState") == "UNMATCHED" and not reasons:
        text += " It remains unpaid or unlinked until a provider operation is observed."
    return {
        "invoiceId": row.get("invoiceId"),
        "status": row.get("status"),
        "reasons": reasons,
        "narrative": text,
        "narrativeSource": "DETERMINISTIC_ROW_FACTS",
    }


def build_operations_report(analysis: dict[str, Any]) -> dict[str, Any]:
    """Build a report narrative beside, never inside, deterministic results."""
    rows = analysis.get("rows", [])
    metrics = analysis.get("metrics", {})
    narratives = [explain_row(row) for row in rows]
    reason_counts = Counter(reason for row in rows for reason in row.get("reasons", []))
    priority_ids = [item["invoiceId"] for item in narratives if item["reasons"]]
    summary = (
        f"Reviewed {metrics.get('invoiceCount', 0)} supplier obligations: "
        f"{metrics.get('readyCount', 0)} ready for review and "
        f"{metrics.get('excludedCount', 0)} excluded or requiring attention."
    )
    return {
        "summary": summary,
        "priorityInvoiceIds": priority_ids,
        "exceptionCounts": dict(sorted(reason_counts.items())),
        "rows": narratives,
        "narrativeBoundary": "Narratives are derived from fixed deterministic rows and cannot change their statuses.",
    }
