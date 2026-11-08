import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from authorization import approve_proposal, create_immutable_proposal
from authorization_ledger import AuthorizationLedger
from paypal_client import PayPalSandboxClient, PayPalSandboxConfig
from paypal_payouts import build_payout_request


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit=-1):
        return self.body


class AuthorizationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.created = create_immutable_proposal(
            accepted=[{"invoiceId": "INV-L", "recipient": "supplier@example.com", "amount": "10.00", "currency": "USD"}],
            currency="USD", total_amount="10.00", policy_version="v1", evidence_refs=[],
            proposal_id="ledger-p", created_at="2026-11-08T10:00:00Z", expires_at="2026-11-09T00:00:00Z",
        )
        self.authorization = approve_proposal(
            proposal=self.created["proposal"], expected_digest=self.created["proposalDigest"],
            approver_id="merchant", approved_at="2026-11-08T10:05:00Z",
        )

    def test_unique_proposal_and_submission_state_transitions(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AuthorizationLedger(Path(directory) / "ledger.sqlite3")
            ledger.record_approval(self.authorization)
            with self.assertRaisesRegex(ValueError, "already been recorded"):
                ledger.record_approval(self.authorization)
            payload = {"sender_batch_header": {"sender_batch_id": "B-1"}, "items": []}
            ledger.reserve_submission(self.authorization["authorizationId"], payload, "2026-11-08T10:06:00Z")
            with self.assertRaisesRegex(ValueError, "in flight"):
                ledger.reserve_submission(self.authorization["authorizationId"], payload, "2026-11-08T10:07:00Z")
            ledger.mark_submitted(self.authorization["authorizationId"], payload, {"batch_header": {"payout_batch_id": "B-1"}}, "2026-11-08T10:08:00Z")
            with self.assertRaisesRegex(ValueError, "already been submitted"):
                ledger.reserve_submission(self.authorization["authorizationId"], payload, "2026-11-08T10:09:00Z")

    def test_in_flight_recovery_requires_matching_provider_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AuthorizationLedger(Path(directory) / "ledger.sqlite3")
            ledger.record_approval(self.authorization)
            payload = {"sender_batch_header": {"sender_batch_id": "B-2"}, "items": []}
            ledger.reserve_submission(self.authorization["authorizationId"], payload, "2026-11-08T10:06:00Z")
            with self.assertRaisesRegex(ValueError, "does not match"):
                ledger.recover_submission(self.authorization["authorizationId"], payload, {"batch_header": {"payout_batch_id": "OTHER"}}, "B-2", "2026-11-08T10:07:00Z")
            ledger.recover_submission(self.authorization["authorizationId"], payload, {"batch_header": {"payout_batch_id": "B-2", "batch_status": "PENDING"}}, "B-2", "2026-11-08T10:08:00Z")

    def test_different_payload_with_same_authorization_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AuthorizationLedger(Path(directory) / "ledger.sqlite3")
            ledger.record_approval(self.authorization)
            ledger.reserve_submission(self.authorization["authorizationId"], {"amount": "10.00"}, "2026-11-08T10:06:00Z")
            with self.assertRaisesRegex(ValueError, "different payload"):
                ledger.reserve_submission(self.authorization["authorizationId"], {"amount": "11.00"}, "2026-11-08T10:07:00Z")

    def test_client_uses_durable_ledger_after_successful_provider_response(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"DURIN_AUTHORIZATION_LEDGER_PATH": str(Path(directory) / "ledger.sqlite3")}, clear=False):
            created = create_immutable_proposal(
                accepted=[{"invoiceId": "INV-C", "recipient": "supplier@example.com", "amount": "10.00", "currency": "USD"}],
                currency="USD", total_amount="10.00", policy_version="v1", evidence_refs=[],
                proposal_id="client-ledger-p", created_at="2026-11-08T10:00:00Z", expires_at="2026-11-09T00:00:00Z",
            )
            approval = approve_proposal(proposal=created["proposal"], expected_digest=created["proposalDigest"], approver_id="merchant", approved_at="2026-11-08T10:05:00Z")
            payload = build_payout_request(proposal=created["proposal"], proposal_digest_value=created["proposalDigest"], authorization=approval, observed_at="2026-11-08T10:10:00Z")
            calls = []

            def opener(request, timeout):
                calls.append(request.full_url)
                if request.full_url.endswith("/v1/oauth2/token"):
                    return FakeResponse(200, {"access_token": "token"})
                return FakeResponse(201, {"batch_header": {"payout_batch_id": "B-1", "batch_status": "PENDING"}})

            client = PayPalSandboxClient(PayPalSandboxConfig("id", "secret", "http://127.0.0.1"), opener=opener)
            client.create_payout(payload, payload["sender_batch_header"]["sender_batch_id"])
            with self.assertRaisesRegex(ValueError, "already been submitted"):
                client.create_payout(payload, payload["sender_batch_header"]["sender_batch_id"])
            self.assertEqual(len(calls), 2)

    def test_authorized_client_refuses_without_durable_ledger(self):
        created = create_immutable_proposal(
            accepted=[{"invoiceId": "INV-N", "recipient": "supplier@example.com", "amount": "10.00", "currency": "USD"}],
            currency="USD", total_amount="10.00", policy_version="v1", evidence_refs=[],
            proposal_id="no-ledger-p", created_at="2026-11-08T10:00:00Z", expires_at="2026-11-09T00:00:00Z",
        )
        approval = approve_proposal(proposal=created["proposal"], expected_digest=created["proposalDigest"], approver_id="merchant", approved_at="2026-11-08T10:05:00Z")
        payload = build_payout_request(proposal=created["proposal"], proposal_digest_value=created["proposalDigest"], authorization=approval, observed_at="2026-11-08T10:10:00Z")
        with patch.dict("os.environ", {}, clear=True):
            client = PayPalSandboxClient(PayPalSandboxConfig("id", "secret", "http://127.0.0.1"), opener=lambda *_: None)
            with self.assertRaisesRegex(ValueError, "durable authorization ledger"):
                client.create_payout(payload, payload["sender_batch_header"]["sender_batch_id"])


if __name__ == "__main__":
    unittest.main()
