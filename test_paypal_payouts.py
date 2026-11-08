import unittest

from authorization import approve_proposal, create_immutable_proposal
from paypal_payouts import build_payout_request, normalize_payout_response, retry_policy


class PayPalPayoutsTests(unittest.TestCase):
    def setUp(self):
        created = create_immutable_proposal(
            accepted=[{"invoiceId": "INV-1", "recipient": "supplier@example.com", "amount": "100.00", "currency": "USD"}],
            currency="USD", total_amount="100.00", policy_version="policy-1", evidence_refs=["source:1"],
            proposal_id="proposal-1", created_at="2026-11-08T12:00:00Z", expires_at="2026-11-08T18:00:00Z",
        )
        self.proposal = created["proposal"]
        self.digest = created["proposalDigest"]
        self.authorization = approve_proposal(
            proposal=self.proposal, expected_digest=self.digest, approver_id="merchant", approved_at="2026-11-08T12:05:00Z"
        )

    def test_build_request_is_not_submission(self):
        request = build_payout_request(
            proposal=self.proposal, proposal_digest_value=self.digest, authorization=self.authorization,
            observed_at="2026-11-08T12:10:00Z",
        )
        self.assertEqual(request["sender_batch_header"]["sender_batch_id"], f"durin-{self.digest[:48]}")
        self.assertEqual(request["durin"]["execution"], "NOT_SUBMITTED")
        self.assertEqual(request["items"][0]["amount"], {"value": "100.00", "currency": "USD"})

    def test_changed_proposal_cannot_be_submitted_from_old_approval(self):
        changed = dict(self.proposal)
        changed["totalAmount"] = "101.00"
        with self.assertRaisesRegex(ValueError, "digest"):
            build_payout_request(
                proposal=changed, proposal_digest_value=self.digest, authorization=self.authorization,
                observed_at="2026-11-08T12:10:00Z",
            )

    def test_provider_states_are_preserved(self):
        result = normalize_payout_response({
            "batch_header": {"payout_batch_id": "B-1", "batch_status": "SUCCESS"},
            "items": [{"payout_item_id": "I-1", "transaction_id": "T-1", "transaction_status": "UNCLAIMED"}],
        })
        self.assertEqual(result["providerBatchStatus"], "SUCCESS")
        self.assertEqual(result["reconciliationStatus"], "REVIEW_ITEM_STATES")
        self.assertEqual(result["items"][0]["providerStatus"], "UNCLAIMED")

    def test_recovery_requires_lookup_after_unknown_outcome(self):
        self.assertEqual(retry_policy(http_status=None, response_received=False), "LOOKUP_BY_SENDER_BATCH_ID_BEFORE_RETRY")
        self.assertEqual(retry_policy(http_status=503, response_received=False), "RETRY_SAME_SENDER_BATCH_ID")


if __name__ == "__main__":
    unittest.main()
