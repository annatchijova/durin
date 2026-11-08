"""Bind PayPal payout responses to deterministic supplier operations."""

from __future__ import annotations

from typing import Any

from paypal_reconciliation import preserve_provider_evidence


def operations_from_payout_response(*, response: dict[str, Any], request_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a provider response into attested, invoice-bound observations.

    A response item is usable only when PayPal returns the request's
    ``sender_item_id``. The adapter refuses positional or amount-only matching.
    """
    header = response.get("batch_header") if isinstance(response, dict) else None
    request_items = request_payload.get("items") if isinstance(request_payload, dict) else None
    if not isinstance(header, dict) or not isinstance(request_items, list) or not request_items:
        raise ValueError("PayPal response and request items are required")
    batch_id = _text(header.get("payout_batch_id"), "payout_batch_id")
    by_sender_id: dict[str, dict[str, Any]] = {}
    for item in request_items:
        if not isinstance(item, dict):
            raise ValueError("request items must be objects")
        sender_item_id = _text(item.get("sender_item_id"), "sender_item_id")
        if sender_item_id in by_sender_id:
            raise ValueError("request sender_item_id values must be unique")
        by_sender_id[sender_item_id] = item
    raw_items = response.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("PayPal response items are required")
    operations: list[dict[str, Any]] = []
    seen_response_ids: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("PayPal response items must be objects")
        sender_item_id = _text(raw.get("sender_item_id"), "sender_item_id")
        if sender_item_id in seen_response_ids:
            raise ValueError("PayPal response contains duplicate sender_item_id")
        request_item = by_sender_id.get(sender_item_id)
        if request_item is None:
            raise ValueError("PayPal response item is not present in the request")
        payout_item_id = _text(raw.get("payout_item_id"), "payout_item_id")
        transaction_id = _text(raw.get("transaction_id"), "transaction_id")
        seen_response_ids.add(sender_item_id)
        evidence = preserve_provider_evidence({
            **raw,
            "payout_batch_id": batch_id,
            "invoiceId": sender_item_id,
        })
        if evidence["parseError"]:
            raise ValueError("PayPal response amount requires reconciliation")
        operations.append({
            "operationId": transaction_id,
            "invoiceId": sender_item_id,
            "recipient": request_item.get("receiver"),
            "amount": evidence["providerAmountValue"],
            "currency": evidence["providerCurrency"],
            "status": evidence["providerStatus"],
            "provider": "paypal",
            "payoutBatchId": batch_id,
            "providerEvidence": evidence,
        })
    return operations


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError(f"{field} is required and bounded")
    return value.strip()
