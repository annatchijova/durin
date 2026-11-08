import json
import unittest
from unittest.mock import patch

import mcp_server


POLICY = json.dumps({
    "merchantName": "Durin Demo Merchant",
    "baseCurrency": "USD",
    "maxAmountPerPayment": "1000.00",
    "maxAmountPerBatch": "2000.00",
    "approvalRequiredAbove": "500.00",
    "approvedRecipients": ["supplier@example.com"],
})


class MerchantAutomationTests(unittest.TestCase):
    def setUp(self):
        self.policy = patch.dict("os.environ", {"DURIN_POLICY_JSON": POLICY}, clear=False)
        self.policy.start()

    def tearDown(self):
        self.policy.stop()

    def test_capabilities_have_no_payment_authority(self):
        result = mcp_server.get_agent_capabilities()
        self.assertNotIn("capture_payment", result["can"])
        self.assertIn("capture_payment", result["cannot"])

    def test_proposal_accepts_valid_invoice_but_never_submits(self):
        result = mcp_server.create_payment_proposal([
            {"invoiceId": "INV-1", "supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com", "amount": "125.00", "currency": "USD"}
        ])
        self.assertEqual(result["accepted"][0]["action"], "READY_FOR_REVIEW")
        self.assertEqual(result["execution"], "NO_PAYMENT_SUBMITTED")
        self.assertTrue(result["humanApprovalRequired"])

    def test_duplicate_is_excluded(self):
        invoice = {"invoiceId": "INV-1", "supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com", "amount": "125.00"}
        result = mcp_server.create_payment_proposal([invoice, {**invoice, "invoiceId": "INV-2"}])
        self.assertEqual(len(result["accepted"]), 1)
        self.assertIn("POSSIBLE_DUPLICATE", result["excluded"][0]["reasons"])

    def test_typo_is_flagged_without_autocorrection(self):
        result = mcp_server.create_payment_proposal([
            {"invoiceId": "INV-1", "supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@examplf.com", "amount": "125.00"}
        ])
        self.assertEqual(result["accepted"], [])
        self.assertIn("POSSIBLE_TYPO", result["excluded"][0]["reasons"])
        self.assertEqual(result["excluded"][0]["recipient"], "supplier@examplf.com")

    def test_limits_and_malformed_amount_fail_closed(self):
        result = mcp_server.create_payment_proposal([
            {"invoiceId": "INV-1", "supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com", "amount": "1001.00"},
        ])
        self.assertIn("EXCEEDS_PER_PAYMENT_LIMIT", result["excluded"][0]["reasons"])

        malformed = mcp_server.create_payment_proposal([
            {"invoiceId": "INV-2", "supplier": "Acme", "invoiceNumber": "A-2", "recipient": "supplier@example.com", "amount": "not-money"},
        ])
        self.assertFalse(malformed["ok"])


if __name__ == "__main__":
    unittest.main()
