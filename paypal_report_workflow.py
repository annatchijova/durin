"""Offline composition of PayPal provider evidence and supplier reporting."""

from __future__ import annotations

from typing import Any

from paypal_operation_adapter import operations_from_payout_response
from paypal_payouts import normalize_payout_response
from supplier_operations import analyze_supplier_batch


def build_paypal_supplier_report(
    *, invoices: list[dict[str, Any]], policy: dict[str, Any], request_payload: dict[str, Any],
    provider_response: dict[str, Any], report_id: str, observed_at: str,
) -> dict[str, Any]:
    """Build a deterministic supplier report from one provider response.

    This function performs no network operation. It normalizes the provider
    response, binds items to the original payout request, and only then passes
    attested observations to the supplier engine.
    """
    normalized = normalize_payout_response(provider_response)
    operations = operations_from_payout_response(response=provider_response, request_payload=request_payload)
    report = analyze_supplier_batch(invoices, operations, policy=policy, observed_at=observed_at)
    report["reportId"] = report_id
    report["paypal"] = {
        "payoutBatchId": normalized["payoutBatchId"],
        "providerBatchStatus": normalized["providerBatchStatus"],
        "reconciliationStatus": normalized["reconciliationStatus"],
        "settlementEvidence": normalized["settlementEvidence"],
    }
    return report
