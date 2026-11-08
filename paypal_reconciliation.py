"""Evidence-first reconciliation for PayPal provider observations."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any


def provider_request_id(scope: str, client_request_id: str) -> str:
    """Derive a stable provider key scoped to one merchant workflow."""
    if not isinstance(scope, str) or not scope.strip() or not isinstance(client_request_id, str) or not client_request_id.strip():
        raise ValueError("scope and client_request_id are required")
    digest = hashlib.sha256(json.dumps([scope, client_request_id], separators=(",", ":")).encode()).hexdigest()
    return f"durin-{digest[:48]}"


def preserve_provider_evidence(item: dict[str, Any]) -> dict[str, Any]:
    """Persist the provider claim even when Durin cannot interpret its money."""
    if not isinstance(item, dict):
        raise ValueError("provider item must be an object")
    status = _text(item.get("transaction_status"), "transaction_status").upper()
    amount = item.get("payout_item", {}).get("amount", {}) if isinstance(item.get("payout_item"), dict) else {}
    raw_value = amount.get("value")
    raw_currency = amount.get("currency")
    parsed_amount = None
    parse_error = None
    try:
        parsed_amount = _amount(raw_value)
        _currency(raw_currency)
    except ValueError as exc:
        parse_error = str(exc)
    return {
        "provider": "paypal",
        "providerItemId": item.get("payout_item_id"),
        "transactionId": item.get("transaction_id"),
        "providerStatus": status,
        "providerAmountValue": raw_value,
        "providerCurrency": raw_currency,
        "parsedAmount": parsed_amount,
        "parseError": parse_error,
        "evidenceStatus": "REQUIRES_RECONCILIATION" if parse_error else "INTERPRETED",
    }


def reconcile_provider_evidence(
    *, expected_amount: str, expected_currency: str, evidence: dict[str, Any]
) -> dict[str, Any]:
    """Compare exact provider evidence without posting a financial event."""
    expected = _amount(expected_amount)
    currency = _currency(expected_currency)
    if evidence.get("parseError"):
        return {"status": "RECONCILIATION_REQUIRED", "reason": "PROVIDER_AMOUNT_UNINTERPRETABLE"}
    if evidence.get("providerStatus") != "SUCCESS":
        return {"status": "PENDING_PROVIDER" if evidence.get("providerStatus") in {"PENDING", "PROCESSING"} else "PROVIDER_EXCEPTION", "reason": evidence.get("providerStatus")}
    if evidence.get("parsedAmount") != expected or str(evidence.get("providerCurrency", "")).upper() != currency:
        return {"status": "RECONCILIATION_REQUIRED", "reason": "AMOUNT_OR_CURRENCY_MISMATCH"}
    return {"status": "MATCHED", "reason": "EXACT_PROVIDER_EVIDENCE"}


def _amount(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("provider amount is missing")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("provider amount is not decimal") from exc
    if parsed <= 0 or parsed.as_tuple().exponent < -2:
        raise ValueError("provider amount has invalid precision")
    return format(parsed.quantize(Decimal("0.01")), "f")


def _currency(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 3 or not value.isalpha():
        raise ValueError("provider currency is invalid")
    return value.upper()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return value.strip()
