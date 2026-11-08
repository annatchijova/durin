#!/usr/bin/env python3
"""No-network red-team probes for Durin's current authority boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from authorization import approve_proposal, create_immutable_proposal
from automation import prepare_proposal
from paypal_client import PayPalSandboxConfig
from paypal_payouts import build_payout_request, normalize_payout_response
from paypal_reconciliation import preserve_provider_evidence, reconcile_provider_evidence
from source_ingestion import validate_invoice_extraction
from source_workflow import build_report_from_extractions


POLICY = {"merchantName": "Probe Merchant", "baseCurrency": "USD", "maxAmountPerPayment": "1000.00", "maxAmountPerBatch": "2000.00", "approvalRequiredAbove": "0.00", "approvedRecipients": ["supplier@example.com"]}
SOURCE = {"sourceId": "probe-source", "source": "/attacker/invoice.txt", "sourceHash": "forged-hash", "content": "Acme A-1 supplier@example.com 100.00 USD 2026-11-30 Hosting"}
CANDIDATE = {"supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com", "amount": "100.00", "currency": "USD", "dueDate": "2026-11-30", "concept": "Hosting", "evidence": {"supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com", "amount": "100.00", "currency": "USD", "dueDate": "2026-11-30", "concept": "Hosting"}}


def proposal_fixture():
    created = create_immutable_proposal(accepted=[{"invoiceId": "INV-1", "recipient": "supplier@example.com", "amount": "100.00", "currency": "USD"}], currency="USD", total_amount="100.00", policy_version="policy-1", evidence_refs=["source:1"], proposal_id="proposal-1", created_at="2026-11-08T12:00:00Z", expires_at="2026-11-08T18:00:00Z")
    approval = approve_proposal(proposal=created["proposal"], expected_digest=created["proposalDigest"], approver_id="merchant", approved_at="2026-11-08T12:05:00Z")
    return created, approval


def main() -> int:
    created, approval = proposal_fixture()
    results = {}
    try:
        accepted = validate_invoice_extraction(source=SOURCE, candidate=CANDIDATE, extractor_version="probe")
        results["RT-01_source_provenance_spoof"] = {"level": "CONFIRMED", "sourceHash": accepted["sourceHash"]}
    except Exception as exc:
        results["RT-01_source_provenance_spoof"] = {"level": "FALSIFIED", "error": str(exc)}

    unsupported = {**CANDIDATE, "evidence": {}}
    report = build_report_from_extractions(policy=POLICY, sources=[SOURCE], candidates_by_source_id={"probe-source": unsupported}, operations=[], report_id="probe", observed_at="2026-11-08T12:00:00Z", extractor_version="probe")
    results["RT-08_review_propagation"] = {"level": "CONFIRMED", "rowStatus": report["rows"][0]["status"], "reasons": report["rows"][0]["reasons"], "requiresReviewCount": report["extraction"]["requiresReviewCount"]}

    fake_authorization = {"status": "APPROVED", "execution": "NOT_EXECUTED", "proposalDigest": created["proposalDigest"], "expiresAt": "2026-11-08T18:00:00Z"}
    try:
        payload = build_payout_request(proposal=created["proposal"], proposal_digest_value=created["proposalDigest"], authorization=fake_authorization, observed_at="2026-11-08T12:10:00Z")
        results["RT-02_bearer_authorization"] = {"level": "CONFIRMED", "authorizationId": payload["durin"]["authorizationId"]}
    except Exception as exc:
        results["RT-02_bearer_authorization"] = {"level": "FALSIFIED", "error": str(exc)}

    second_approval = approve_proposal(proposal=created["proposal"], expected_digest=created["proposalDigest"], approver_id="merchant", approved_at="2026-11-08T12:06:00Z")
    first_build = build_payout_request(proposal=created["proposal"], proposal_digest_value=created["proposalDigest"], authorization=approval, observed_at="2026-11-08T12:10:00Z")
    second_build = build_payout_request(proposal=created["proposal"], proposal_digest_value=created["proposalDigest"], authorization=approval, observed_at="2026-11-08T12:10:00Z")
    results["RT-03_replay"] = {"level": "CONFIRMED", "secondApproval": bool(second_approval), "sameBatchId": first_build["sender_batch_header"]["sender_batch_id"] == second_build["sender_batch_header"]["sender_batch_id"]}

    forged_evidence = {"providerStatus": "SUCCESS", "parsedAmount": "100.00", "providerCurrency": "USD", "parseError": None, "providerItemId": "WRONG"}
    results["RT-04_identity_binding"] = {"level": "CONFIRMED", "result": reconcile_provider_evidence(expected_amount="100.00", expected_currency="USD", evidence=forged_evidence)}

    special_results = {}
    for value in ("NaN", "Infinity"):
        try:
            special_results[value] = preserve_provider_evidence({"transaction_status": "SUCCESS", "payout_item": {"amount": {"value": value, "currency": "USD"}}})["evidenceStatus"]
        except Exception as exc:
            special_results[value] = f"ESCAPED_{type(exc).__name__}: {exc}"
    results["RT-05_special_numbers"] = {"level": "CONFIRMED", "results": special_results}

    try:
        PayPalSandboxConfig("id", "secret", "https://api-m.sandbox.paypal.com:443@127.0.0.1").validate()
        results["RT-06_userinfo_url"] = {"level": "CONFIRMED"}
    except Exception as exc:
        results["RT-06_userinfo_url"] = {"level": "FALSIFIED", "error": str(exc)}

    results["RT-07_duplicate_provider_ids"] = {"level": "CONFIRMED", "result": normalize_payout_response({"batch_header": {"payout_batch_id": "B-1", "batch_status": "SUCCESS"}, "items": [{"payout_item_id": "ITEM-1", "transaction_status": "SUCCESS"}, {"payout_item_id": "ITEM-1", "transaction_status": "SUCCESS"}]})["reconciliationStatus"]}
    results["RT-09_empty_allowlist"] = {"level": "CODE_FACT", "accepted": bool(prepare_proposal([{"invoiceId": "I", "supplier": "Acme", "invoiceNumber": "A-1", "recipient": "attacker@example.com", "amount": "1.00", "currency": "USD"}], {**POLICY, "approvedRecipients": []})["accepted"])}
    print(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
