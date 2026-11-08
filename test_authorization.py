import copy
import unittest

from authorization import approve_proposal, create_immutable_proposal, proposal_digest


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.created = create_immutable_proposal(
            accepted=[{"invoiceId": "INV-1", "recipient": "supplier@example.com", "amount": "100.00", "currency": "USD"}],
            currency="USD",
            total_amount="100.00",
            policy_version="policy-1",
            evidence_refs=["source:abc"],
            proposal_id="proposal-1",
            created_at="2026-11-08T12:00:00Z",
            expires_at="2026-11-08T18:00:00Z",
        )

    def test_approval_binds_to_digest_and_does_not_execute(self):
        result = approve_proposal(
            proposal=self.created["proposal"],
            expected_digest=self.created["proposalDigest"],
            approver_id="merchant-user",
            approved_at="2026-11-08T12:05:00Z",
        )
        self.assertEqual(result["status"], "APPROVED")
        self.assertEqual(result["execution"], "NOT_EXECUTED")

    def test_changed_amount_invalidates_authorization(self):
        changed = copy.deepcopy(self.created["proposal"])
        changed["items"][0]["amount"] = "101.00"
        with self.assertRaisesRegex(ValueError, "digest"):
            approve_proposal(proposal=changed, expected_digest=self.created["proposalDigest"], approver_id="merchant-user", approved_at="2026-11-08T12:05:00Z")

    def test_replay_of_approved_proposal_is_rejected(self):
        proposal = copy.deepcopy(self.created["proposal"])
        proposal["status"] = "APPROVED"
        with self.assertRaisesRegex(ValueError, "not pending"):
            approve_proposal(proposal=proposal, expected_digest=proposal_digest(proposal), approver_id="merchant-user", approved_at="2026-11-08T12:05:00Z")


if __name__ == "__main__":
    unittest.main()
