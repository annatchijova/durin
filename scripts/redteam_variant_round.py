"""Offline variant-analysis probes for the Durin red-team audit.

This script does not use the network, credentials, PayPal Sandbox, or a real
payment. It exercises sibling entry points and state combinations that share
the same security invariants.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from authorization import proposal_digest
from automation import prepare_proposal
from paypal_client import PayPalSandboxConfig
from paypal_payouts import build_payout_request, normalize_payout_response
from paypal_reconciliation import preserve_provider_evidence
from source_ingestion import validate_invoice_extraction
from source_workflow import build_report_from_extractions


POLICY = {
    "merchantName": "Durin",
    "baseCurrency": "USD",
    "maxAmountPerPayment": "1000.00",
    "maxAmountPerBatch": "2000.00",
    "approvalRequiredAbove": "500.00",
    "approvedRecipients": ["supplier@example.com"],
}
SOURCE = {
    "sourceId": "src-1",
    "sourceHash": "hash-1",
    "source": "/safe/invoice.txt",
    "kind": "INVOICE",
    "content": "Invoice A-1 for 125.00 USD from Acme supplier@example.com",
}
CANDIDATE = {
    "supplier": "Acme",
    "invoiceNumber": "A-1",
    "recipient": "supplier@example.com",
    "amount": "125.00",
    "currency": "USD",
    "dueDate": "2026-12-01",
    "concept": "Services",
    "evidence": {"supplier": "Invoice A-1 for 125.00 USD from Acme supplier@example.com"},
}


def check(label: str, operation) -> None:
    try:
        result = operation()
        print(json.dumps({"label": label, "outcome": "RETURNED_FOR_REVIEW", "result": result}, default=str))
    except Exception as exc:  # Deliberately record boundary failures as evidence.
        print(json.dumps({"label": label, "outcome": "REJECTED_OR_ESCAPED", "error": type(exc).__name__, "message": str(exc)}))


def main() -> None:
    check(
        "duplicate_source_id",
        lambda: build_report_from_extractions(
            policy=POLICY,
            sources=[SOURCE, {**SOURCE, "sourceHash": "hash-2"}],
            candidates_by_source_id={"src-1": CANDIDATE},
            operations=[],
            report_id="variant-1",
            observed_at="2026-11-08T12:00:00Z",
            extractor_version="probe",
        )["extraction"],
    )
    check(
        "contract_as_invoice",
        lambda: build_report_from_extractions(
            policy=POLICY,
            sources=[{**SOURCE, "kind": "CONTRACT"}],
            candidates_by_source_id={"src-1": CANDIDATE},
            operations=[],
            report_id="variant-2",
            observed_at="2026-11-08T12:00:00Z",
            extractor_version="probe",
        )["extraction"],
    )
    check(
        "missing_content_candidate",
        lambda: validate_invoice_extraction(
            source={key: value for key, value in SOURCE.items() if key != "content"},
            candidate=CANDIDATE,
            extractor_version="probe",
        )["requiresReview"],
    )
    check(
        "review_marker_direct_proposal",
        lambda: prepare_proposal(
            [{**CANDIDATE, "invoiceId": "INV-1", "requiresReview": True}], POLICY
        ),
    )
    check(
        "provider_success_without_ids",
        lambda: normalize_payout_response(
            {"batch_header": {"batch_status": "SUCCESS"}, "items": [{"transaction_status": "SUCCESS"}]}
        ),
    )

    proposal = {
        "schemaVersion": 1,
        "proposalId": "p",
        "flow": "PAYABLE",
        "items": [
            {"invoiceId": "INV-1", "recipient": "supplier@example.com", "amount": "10.00", "currency": "USD"},
            {"invoiceId": "INV-1", "recipient": "supplier@example.com", "amount": "10.00", "currency": "USD"},
        ],
        "currency": "USD",
        "totalAmount": "20.00",
        "policyVersion": "v1",
        "evidenceRefs": [],
        "createdAt": "2026-11-08T09:00:00Z",
        "expiresAt": "2026-11-09T00:00:00Z",
        "status": "PENDING_APPROVAL",
        "execution": "NO_PAYMENT_SUBMITTED",
    }
    digest = proposal_digest(proposal)
    authorization = {
        "proposalDigest": digest,
        "status": "APPROVED",
        "execution": "NOT_EXECUTED",
        "authorizationId": "auth",
        "approvedAt": "2026-11-08T10:00:00Z",
        "expiresAt": "2026-11-09T00:00:00Z",
    }
    check(
        "duplicate_sender_item_id",
        lambda: build_payout_request(
            proposal=proposal,
            proposal_digest_value=digest,
            authorization=authorization,
            observed_at="2026-11-08T12:00:00Z",
        )["items"],
    )
    check(
        "observed_before_approval",
        lambda: build_payout_request(
            proposal={**proposal, "items": [proposal["items"][0]], "totalAmount": "10.00"},
            proposal_digest_value=proposal_digest({**proposal, "items": [proposal["items"][0]], "totalAmount": "10.00"}),
            authorization={
                **authorization,
                "proposalDigest": proposal_digest({**proposal, "items": [proposal["items"][0]], "totalAmount": "10.00"}),
                "approvedAt": "2026-11-08T12:05:00Z",
            },
            observed_at="2026-11-08T12:00:00Z",
        ),
    )
    check(
        "naive_observed_at",
        lambda: build_payout_request(
            proposal=proposal,
            proposal_digest_value=digest,
            authorization=authorization,
            observed_at="2026-11-08T12:00:00",
        ),
    )
    check("timeout_nan", lambda: PayPalSandboxConfig("id", "secret", timeout_seconds=float("nan")).validate())
    check(
        "provider_infinity",
        lambda: preserve_provider_evidence(
            {"transaction_status": "SUCCESS", "payout_item": {"amount": {"value": "Infinity", "currency": "USD"}}}
        ),
    )


if __name__ == "__main__":
    main()
