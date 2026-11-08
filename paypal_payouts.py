"""PayPal Payouts boundary without network access or credentials.

This module builds a request only after a human-approved digest and normalizes
provider responses without collapsing PayPal's states into a boolean.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from automation import format_money, parse_amount
from authorization import proposal_digest


SANDBOX_API_BASE = "https://api-m.sandbox.paypal.com"
SUPPORTED_RECIPIENT_TYPE = "EMAIL"
PENDING_BATCH_STATES = {"PENDING", "PROCESSING"}
FINAL_SUCCESS_BATCH_STATE = "SUCCESS"


def build_payout_request(
    *, proposal: dict[str, Any], proposal_digest_value: str, authorization: dict[str, Any],
    observed_at: str,
) -> dict[str, Any]:
    """Build a PayPal Payouts v1 payload, without submitting it."""
    if authorization.get("status") != "APPROVED" or authorization.get("execution") != "NOT_EXECUTED":
        raise ValueError("authorization is not an unused human approval")
    if authorization.get("proposalDigest") != proposal_digest_value:
        raise ValueError("authorization digest does not match the proposal")
    if proposal_digest(proposal) != proposal_digest_value:
        raise ValueError("proposal digest does not match the presented proposal")
    _timestamp(observed_at, "observed_at")
    if _timestamp(authorization.get("expiresAt"), "authorization.expiresAt") < _timestamp(observed_at, "observed_at"):
        raise ValueError("authorization is expired")
    if proposal.get("status") != "PENDING_APPROVAL":
        raise ValueError("proposal is not an approved execution source")
    items = proposal.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("proposal must contain payout items")
    currency = _currency(proposal.get("currency"))
    payout_items = []
    total = parse_amount(proposal.get("totalAmount"), "proposal.totalAmount")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("proposal items must be objects")
        recipient = _text(item.get("recipient"), "item.recipient")
        item_currency = _currency(item.get("currency", currency))
        if item_currency != currency:
            raise ValueError("all payout items must use the proposal currency")
        amount = parse_amount(item.get("amount"), "item.amount")
        payout_items.append(
            {
                "recipient_type": SUPPORTED_RECIPIENT_TYPE,
                "amount": {"value": format_money(amount), "currency": item_currency},
                "note": f"Durin approved supplier payout {item.get('invoiceId', '')}"[:255],
                "sender_item_id": _text(item.get("invoiceId"), "item.invoiceId"),
                "receiver": recipient,
            }
        )
    if sum((parse_amount(item["amount"]["value"]) for item in payout_items), start=Decimal("0")) != total:
        raise ValueError("proposal total does not equal payout item total")
    sender_batch_id = f"durin-{proposal_digest_value[:48]}"
    return {
        "sender_batch_header": {
            "sender_batch_id": sender_batch_id,
            "recipient_type": SUPPORTED_RECIPIENT_TYPE,
            "email_subject": "Durin approved supplier payout",
        },
        "items": payout_items,
        "durin": {
            "proposalDigest": proposal_digest_value,
            "authorizationId": authorization.get("authorizationId"),
            "observedAt": observed_at,
            "execution": "NOT_SUBMITTED",
        },
    }


def normalize_payout_response(response: dict[str, Any]) -> dict[str, Any]:
    """Preserve PayPal batch/item statuses and derive review-only state."""
    if not isinstance(response, dict):
        raise ValueError("PayPal response must be an object")
    header = response.get("batch_header")
    if not isinstance(header, dict):
        raise ValueError("PayPal response is missing batch_header")
    batch_status = _text(header.get("batch_status"), "batch_status").upper()
    raw_items = response.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("PayPal response items must be an array")
    items = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("PayPal response item must be an object")
        status = _text(raw.get("transaction_status"), "transaction_status").upper()
        items.append(
            {
                "payoutItemId": raw.get("payout_item_id"),
                "transactionId": raw.get("transaction_id"),
                "providerStatus": status,
                "reconciliationStatus": _item_state(status),
                "error": raw.get("errors"),
            }
        )
    if batch_status == FINAL_SUCCESS_BATCH_STATE and items and all(item["providerStatus"] == "SUCCESS" for item in items):
        reconciliation = "PROVIDER_COMPLETED"
    elif batch_status in PENDING_BATCH_STATES:
        reconciliation = "PENDING_PROVIDER"
    elif batch_status in {"DENIED", "CANCELED"}:
        reconciliation = "PROVIDER_FAILED"
    elif batch_status == FINAL_SUCCESS_BATCH_STATE:
        reconciliation = "REVIEW_ITEM_STATES"
    else:
        reconciliation = "UNKNOWN_PROVIDER_STATE"
    return {
        "payoutBatchId": header.get("payout_batch_id"),
        "providerBatchStatus": batch_status,
        "reconciliationStatus": reconciliation,
        "items": items,
        "settlementEvidence": "PAYPAL_PROVIDER_STATUS_ONLY",
    }


def retry_policy(*, http_status: int | None, response_received: bool) -> str:
    """Return a recovery instruction, never an automatic payment retry."""
    if not response_received and http_status is None:
        return "LOOKUP_BY_SENDER_BATCH_ID_BEFORE_RETRY"
    if http_status is not None and 500 <= http_status <= 599:
        return "RETRY_SAME_SENDER_BATCH_ID"
    return "DO_NOT_RETRY_WITHOUT_REVIEW"


def _item_state(status: str) -> str:
    if status == "SUCCESS":
        return "COMPLETED"
    if status in {"PENDING", "PROCESSING"}:
        return "PENDING"
    if status in {"RETURNED", "REFUNDED", "UNCLAIMED"}:
        return "EXCEPTION"
    return "FAILED_OR_REVIEW"


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError(f"{field} is required and bounded")
    return value.strip()


def _currency(value: Any) -> str:
    result = _text(value, "currency").upper()
    if len(result) != 3 or not result.isalpha():
        raise ValueError("currency must be a three-letter code")
    return result


def _timestamp(value: Any, field: str) -> datetime:
    try:
        return datetime.fromisoformat(_text(value, field).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
