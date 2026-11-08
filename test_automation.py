import unittest
from decimal import Decimal

from automation import find_duplicates, parse_amount, prepare_proposal


POLICY = {
    "baseCurrency": "USD",
    "maxAmountPerPayment": "1000.00",
    "maxAmountPerBatch": "2000.00",
    "approvalRequiredAbove": "500.00",
    "approvedRecipients": ["supplier@example.com"],
}


def invoice(invoice_id: str, amount: str = "125.00", recipient: str = "supplier@example.com"):
    return {
        "invoiceId": invoice_id,
        "supplier": "Acme",
        "invoiceNumber": "A-1",
        "recipient": recipient,
        "amount": amount,
        "currency": "USD",
    }


class AutomationTests(unittest.TestCase):
    def test_decimal_parser_does_not_use_float(self):
        self.assertEqual(parse_amount("0.10") + parse_amount("0.20"), Decimal("0.30"))

    def test_duplicate_groups_are_deterministic(self):
        groups = find_duplicates([invoice("INV-1"), invoice("INV-2")])
        self.assertEqual(groups[0]["invoiceIds"], ["INV-1", "INV-2"])

    def test_proposal_preserves_human_boundary(self):
        result = prepare_proposal([invoice("INV-1", "750.00")], POLICY)
        self.assertEqual(result["accepted"][0]["action"], "READY_FOR_REVIEW")
        self.assertTrue(result["accepted"][0]["approvalRequired"])
        self.assertTrue(result["humanApprovalRequired"])
        self.assertEqual(result["execution"], "NO_PAYMENT_SUBMITTED")

    def test_invalid_recipient_is_excluded_without_correction(self):
        result = prepare_proposal([invoice("INV-1", recipient="supplier@examplf.com")], POLICY)
        self.assertEqual(result["accepted"], [])
        self.assertIn("POSSIBLE_TYPO", result["excluded"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
