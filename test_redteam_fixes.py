import tempfile
import unittest
from pathlib import Path

from authorization import approve_proposal, create_immutable_proposal, proposal_digest
from automation import prepare_proposal
from paypal_client import PayPalSandboxClient, PayPalSandboxConfig
from paypal_payouts import build_payout_request, mark_authorization_submitted, normalize_payout_response
from paypal_reconciliation import preserve_provider_evidence, reconcile_provider_evidence
from source_ingestion import list_sources, validate_invoice_extraction
from source_workflow import build_report_from_extractions
from supplier_operations import analyze_supplier_batch


POLICY = {
    "merchantName": "Test Merchant",
    "baseCurrency": "USD",
    "maxAmountPerPayment": "1000.00",
    "maxAmountPerBatch": "2000.00",
    "approvalRequiredAbove": "500.00",
    "approvedRecipients": ["supplier@example.com"],
}


def invoice(**changes):
    value = {
        "invoiceId": "INV-1",
        "supplier": "Acme",
        "invoiceNumber": "A-1",
        "recipient": "supplier@example.com",
        "amount": "100.00",
        "currency": "USD",
    }
    value.update(changes)
    return value


class RedTeamFixTests(unittest.TestCase):
    def test_unattested_source_is_rejected(self):
        source = {"sourceId": "abc", "sourceHash": "hash", "source": "/tmp/invoice.txt", "kind": "INVOICE", "content": "Acme 100.00"}
        candidate = {"supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com", "amount": "100.00", "currency": "USD", "dueDate": "2026-12-01", "concept": "Services", "evidence": {}}
        with self.assertRaisesRegex(ValueError, "provenance|attestation"):
            validate_invoice_extraction(source=source, candidate=candidate, extractor_version="test")

    def test_field_value_must_appear_in_its_excerpt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invoice.txt"
            path.write_text("Amount: 100.00", encoding="utf-8")
            source = list_sources(directory)[0]
            candidate = {
                "supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com",
                "amount": "999.99", "currency": "USD", "dueDate": "2026-12-01", "concept": "Services",
                "evidence": {"amount": "Amount:"},
            }
            result = validate_invoice_extraction(source=source, candidate=candidate, extractor_version="test")
            self.assertTrue(result["requiresReview"])

    def test_duplicate_and_contract_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invoice.txt"
            path.write_text("Acme invoice A-1", encoding="utf-8")
            source = list_sources(directory)[0]
            candidate = {
                "supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com",
                "amount": "100.00", "currency": "USD", "dueDate": "2026-12-01", "concept": "Services",
                "evidence": {},
            }
            with self.assertRaisesRegex(ValueError, "sourceId must be unique"):
                build_report_from_extractions(
                    policy=POLICY, sources=[source, source], candidates_by_source_id={source["sourceId"]: candidate},
                    operations=[], report_id="r", observed_at="2026-11-08T12:00:00Z", extractor_version="test",
                )
            contract_path = Path(directory) / "contract.txt"
            contract_path.write_text("Acme invoice A-1", encoding="utf-8")
            contract = next(item for item in list_sources(directory) if item["kind"] == "CONTRACT")
            report = build_report_from_extractions(
                policy=POLICY, sources=[contract], candidates_by_source_id={contract["sourceId"]: candidate},
                operations=[], report_id="r", observed_at="2026-11-08T12:00:00Z", extractor_version="test",
            )
            self.assertEqual(report["metrics"]["invoiceCount"], 0)
            rejected = next(item for item in report["sourceManifest"] if item["validationStatus"] == "EXTRACTION_REJECTED")
            self.assertIn("not eligible", rejected["rejectionReason"])

    def test_review_marker_and_empty_allowlist_fail_closed(self):
        result = prepare_proposal([invoice(requiresReview=True)], POLICY)
        self.assertEqual(result["accepted"], [])
        self.assertIn("REQUIRES_SOURCE_REVIEW", result["excluded"][0]["reasons"])
        with self.assertRaisesRegex(ValueError, "approvedRecipients"):
            prepare_proposal([invoice(recipient="attacker@example.com")], {**POLICY, "approvedRecipients": []})

    def test_operation_identity_and_provider_provenance_are_required(self):
        foreign = [{"operationId": "P-1", "invoiceNumber": "A-1", "recipient": "other@example.com", "amount": "100.00", "currency": "USD", "status": "SUCCESS"}]
        result = analyze_supplier_batch([invoice()], foreign, policy=POLICY)
        self.assertEqual(result["rows"][0]["operationState"], "UNMATCHED")
        fake = [{"operationId": "P-2", "invoiceId": "INV-1", "amount": "100.00", "currency": "USD", "status": "SUCCESS"}]
        result = analyze_supplier_batch([invoice()], fake, policy=POLICY)
        self.assertIn("PROVIDER_EVIDENCE_REQUIRED", result["rows"][0]["reasons"])

    def test_sibling_engine_closes_allowlist_and_partial_provenance(self):
        with self.assertRaisesRegex(ValueError, "approvedRecipients"):
            analyze_supplier_batch([invoice(recipient="attacker@example.com")], [], policy={**POLICY, "approvedRecipients": []})
        partial = [{"operationId": "P-3", "invoiceId": "INV-1", "amount": "40.00", "currency": "USD", "status": "SUCCESS", "provider": "paypal", "transactionId": "T-3"}]
        result = analyze_supplier_batch([invoice()], partial, policy=POLICY)
        self.assertIn("PROVIDER_EVIDENCE_REQUIRED", result["rows"][0]["reasons"])

    def test_authorization_proof_and_replay_guard(self):
        created = create_immutable_proposal(accepted=[invoice()], currency="USD", total_amount="100.00", policy_version="v1", evidence_refs=[], proposal_id="replay-p", created_at="2026-11-08T10:00:00Z", expires_at="2026-11-09T00:00:00Z")
        fake = {"proposalId": "replay-p", "proposalDigest": created["proposalDigest"], "status": "APPROVED", "execution": "NOT_EXECUTED", "authorizationId": "forged", "approverId": "merchant", "approvedAt": "2026-11-08T10:05:00Z", "expiresAt": "2026-11-09T00:00:00Z"}
        with self.assertRaisesRegex(ValueError, "proof"):
            build_payout_request(proposal=created["proposal"], proposal_digest_value=created["proposalDigest"], authorization=fake, observed_at="2026-11-08T10:10:00Z")
        approved = approve_proposal(proposal=created["proposal"], expected_digest=created["proposalDigest"], approver_id="merchant", approved_at="2026-11-08T10:05:00Z")
        build_payout_request(proposal=created["proposal"], proposal_digest_value=created["proposalDigest"], authorization=approved, observed_at="2026-11-08T10:10:00Z")
        mark_authorization_submitted(approved["authorizationId"])
        with self.assertRaisesRegex(ValueError, "consumed"):
            mark_authorization_submitted(approved["authorizationId"])

    def test_provider_evidence_requires_local_attestation_and_proposal_amounts_are_positive(self):
        forged = {"provider": "paypal", "providerItemId": "I", "transactionId": "T", "providerStatus": "SUCCESS", "providerAmountValue": "100.00", "providerCurrency": "USD", "parsedAmount": "100.00", "parseError": None, "evidenceStatus": "INTERPRETED"}
        self.assertEqual(reconcile_provider_evidence(expected_amount="100.00", expected_currency="USD", evidence=forged)["reason"], "PROVIDER_EVIDENCE_UNATTESTED")
        with self.assertRaisesRegex(ValueError, "positive"):
            create_immutable_proposal(accepted=[invoice(amount="-1.00")], currency="USD", total_amount="-1.00", policy_version="v1", evidence_refs=[], proposal_id="negative-p", created_at="2026-11-08T10:00:00Z", expires_at="2026-11-09T00:00:00Z")

    def test_binding_fields_and_provenance_timestamps_are_attested(self):
        evidence = preserve_provider_evidence({
            "invoiceId": "OTHER", "invoiceNumber": "A-1", "payout_batch_id": "B-1",
            "payout_item_id": "I-1", "transaction_id": "T-1", "transaction_status": "SUCCESS",
            "payout_item": {"amount": {"value": "100.00", "currency": "USD"}},
        })
        operation = {"operationId": "P-1", "invoiceId": "INV-1", "invoiceNumber": "A-1", "amount": "100.00", "currency": "USD", "status": "SUCCESS", "payoutBatchId": "B-1", "providerEvidence": evidence}
        result = analyze_supplier_batch([invoice()], [operation], policy=POLICY)
        self.assertIn("PROVIDER_EVIDENCE_REQUIRED", result["rows"][0]["reasons"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invoice.txt"
            path.write_text("Acme A-1 supplier@example.com 100.00 USD 2026-12-01 Services", encoding="utf-8")
            source = list_sources(directory)[0]
            source["observedAt"] = "2099-01-01T00:00:00Z"
            with self.assertRaisesRegex(ValueError, "attestation"):
                validate_invoice_extraction(source=source, candidate={"supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com", "amount": "100.00", "currency": "USD", "dueDate": "2026-12-01", "concept": "Services", "evidence": {}}, extractor_version="test")

    def test_authorization_id_mutation_invalidates_proof(self):
        created = create_immutable_proposal(accepted=[invoice()], currency="USD", total_amount="100.00", policy_version="v1", evidence_refs=[], proposal_id="auth-id-p", created_at="2026-11-08T10:00:00Z", expires_at="2026-11-09T00:00:00Z")
        approved = approve_proposal(proposal=created["proposal"], expected_digest=created["proposalDigest"], approver_id="merchant", approved_at="2026-11-08T10:05:00Z")
        mutated = {**approved, "authorizationId": "forged-id"}
        with self.assertRaisesRegex(ValueError, "proof"):
            build_payout_request(proposal=created["proposal"], proposal_digest_value=created["proposalDigest"], authorization=mutated, observed_at="2026-11-08T10:10:00Z")

    def test_provider_response_identity_is_required(self):
        with self.assertRaisesRegex(ValueError, "payout_batch_id"):
            normalize_payout_response({"batch_header": {"batch_status": "SUCCESS"}, "items": [{"transaction_status": "SUCCESS"}]})
        evidence = preserve_provider_evidence({"transaction_status": "SUCCESS", "payout_item": {"amount": {"value": "Infinity", "currency": "USD"}}})
        self.assertEqual(evidence["evidenceStatus"], "REQUIRES_RECONCILIATION")
        self.assertEqual(reconcile_provider_evidence(expected_amount="100.00", expected_currency="USD", evidence=evidence)["status"], "RECONCILIATION_REQUIRED")

    def test_proposal_state_identity_and_temporal_order_are_enforced(self):
        accepted = [invoice()]
        with self.assertRaisesRegex(ValueError, "total"):
            create_immutable_proposal(accepted=accepted, currency="USD", total_amount="99.00", policy_version="v1", evidence_refs=[], proposal_id="p", created_at="2026-11-08T10:00:00Z", expires_at="2026-11-09T00:00:00Z")
        created = create_immutable_proposal(accepted=accepted, currency="USD", total_amount="100.00", policy_version="v1", evidence_refs=[], proposal_id="p", created_at="2026-11-08T10:00:00Z", expires_at="2026-11-09T00:00:00Z")
        proposal = {**created["proposal"], "execution": "EXECUTED"}
        digest = proposal_digest(proposal)
        authorization = {"proposalId": "p", "proposalDigest": digest, "status": "APPROVED", "execution": "NOT_EXECUTED", "authorizationId": "a", "approvedAt": "2026-11-08T12:05:00Z", "expiresAt": "2026-11-09T00:00:00Z"}
        with self.assertRaisesRegex(ValueError, "execution state"):
            build_payout_request(proposal=proposal, proposal_digest_value=digest, authorization=authorization, observed_at="2026-11-08T12:10:00Z")
        approved = approve_proposal(proposal=created["proposal"], expected_digest=created["proposalDigest"], approver_id="merchant", approved_at="2026-11-08T12:05:00Z")
        with self.assertRaisesRegex(ValueError, "precedes"):
            build_payout_request(proposal=created["proposal"], proposal_digest_value=created["proposalDigest"], authorization=approved, observed_at="2026-11-08T12:00:00Z")

    def test_configuration_and_request_binding_fail_closed(self):
        with self.assertRaises(ValueError):
            PayPalSandboxConfig("id", "secret", timeout_seconds=float("nan")).validate()
        with self.assertRaises(ValueError):
            PayPalSandboxConfig("id", "secret", "https://api-m.sandbox.paypal.com:443@127.0.0.1").validate()
        client = PayPalSandboxClient(PayPalSandboxConfig("id", "secret", "http://127.0.0.1"), opener=lambda *_: None)
        with self.assertRaisesRegex(ValueError, "match payload"):
            client.create_payout({"sender_batch_header": {"sender_batch_id": "A"}}, "B")


if __name__ == "__main__":
    unittest.main()
