import unittest

from supplier_operations import analyze_supplier_batch


POLICY = {
    "approvedRecipients": ["supplier@example.com"],
    "maxAmountPerPayment": "1000.00",
}


def invoice(invoice_id="INV-1", amount="100.00", recipient="supplier@example.com", number="A-1"):
    return {
        "invoiceId": invoice_id,
        "supplier": "Acme",
        "invoiceNumber": number,
        "recipient": recipient,
        "amount": amount,
        "currency": "USD",
        "history": [{"amount": "100.00", "currency": "USD"}],
    }


class SupplierOperationsTests(unittest.TestCase):
    def test_duplicate_and_typo_are_separate_reasons(self):
        result = analyze_supplier_batch([invoice(), invoice("INV-2"), invoice("INV-3", recipient="supplier@examplf.com", number="A-3")], [], policy=POLICY)
        self.assertEqual(result["metrics"]["reasonCounts"]["POSSIBLE_DUPLICATE"], 1)
        self.assertEqual(result["metrics"]["reasonCounts"]["POSSIBLE_TYPO"], 1)

    def test_price_alert_is_not_silent(self):
        result = analyze_supplier_batch([invoice(amount="120.00")], [], policy=POLICY)
        self.assertIn("PRICE_ALERT", result["rows"][0]["reasons"])
        self.assertEqual(result["rows"][0]["operationState"], "UNMATCHED")

    def test_two_operations_are_ambiguous(self):
        operations = [
            {"operationId": "P-1", "invoiceId": "INV-1", "amount": "100.00", "currency": "USD", "status": "SUCCESS"},
            {"operationId": "P-2", "invoiceId": "INV-1", "amount": "100.00", "currency": "USD", "status": "SUCCESS"},
        ]
        result = analyze_supplier_batch([invoice()], operations, policy=POLICY)
        self.assertEqual(result["rows"][0]["operationState"], "AMBIGUOUS")
        self.assertIn("AMBIGUOUS_OPERATION", result["rows"][0]["reasons"])

    def test_mismatched_currency_does_not_reconcile(self):
        operations = [{"operationId": "P-1", "invoiceId": "INV-1", "amount": "100.00", "currency": "EUR", "status": "SUCCESS"}]
        result = analyze_supplier_batch([invoice()], operations, policy=POLICY)
        self.assertEqual(result["rows"][0]["operationState"], "MISMATCHED")
        self.assertIn("OPERATION_MISMATCH", result["rows"][0]["reasons"])

    def test_metrics_never_claim_execution(self):
        result = analyze_supplier_batch([invoice()], [], policy=POLICY)
        self.assertEqual(result["execution"], "NO_PAYMENT_SUBMITTED")
        self.assertTrue(result["humanApprovalRequired"])

    def test_overdue_invoice_is_explicit_against_observation_date(self):
        item = invoice()
        item["dueDate"] = "2026-11-01"
        result = analyze_supplier_batch([item], [], policy=POLICY, observed_at="2026-11-08T12:00:00Z")
        self.assertIn("OVERDUE", result["rows"][0]["reasons"])
        self.assertEqual(result["rows"][0]["dueDate"], "2026-11-01")

    def test_paid_invoice_is_not_marked_overdue(self):
        item = invoice()
        item["dueDate"] = "2026-11-01"
        operations = [{"operationId": "P-1", "invoiceId": "INV-1", "amount": "100.00", "currency": "USD", "status": "SUCCESS"}]
        result = analyze_supplier_batch([item], operations, policy=POLICY, observed_at="2026-11-08T12:00:00Z")
        self.assertNotIn("OVERDUE", result["rows"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
