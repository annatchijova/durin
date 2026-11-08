import unittest

from supplier_operations import analyze_supplier_batch
from paypal_reconciliation import preserve_provider_evidence


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


def operation(operation_id="P-1", amount="100.00", currency="USD", status="SUCCESS", invoice_id="INV-1"):
    evidence = preserve_provider_evidence({
        "invoiceId": invoice_id, "invoiceNumber": "A-1", "payout_batch_id": "B-1",
        "payout_item_id": f"I-{operation_id}", "transaction_id": f"T-{operation_id}",
        "transaction_status": status,
        "payout_item": {"amount": {"value": amount, "currency": currency}},
    })
    return {"operationId": operation_id, "invoiceId": invoice_id, "invoiceNumber": "A-1", "amount": amount, "currency": currency, "status": status, "payoutBatchId": "B-1", "providerEvidence": evidence}


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
            operation("P-1"),
            operation("P-2"),
        ]
        result = analyze_supplier_batch([invoice()], operations, policy=POLICY)
        self.assertEqual(result["rows"][0]["operationState"], "AMBIGUOUS")
        self.assertIn("AMBIGUOUS_OPERATION", result["rows"][0]["reasons"])

    def test_mismatched_currency_does_not_reconcile(self):
        operations = [operation(currency="EUR")]
        result = analyze_supplier_batch([invoice()], operations, policy=POLICY)
        self.assertEqual(result["rows"][0]["operationState"], "MISMATCHED")
        self.assertIn("OPERATION_MISMATCH", result["rows"][0]["reasons"])

    def test_partial_operation_is_not_treated_as_paid(self):
        operations = [operation(amount="40.00")]
        result = analyze_supplier_batch([invoice()], operations, policy=POLICY)
        row = result["rows"][0]
        self.assertEqual(row["operationState"], "PARTIALLY_MATCHED")
        self.assertEqual(row["recognizedAmount"], "40.00")
        self.assertIn("PARTIAL_OPERATION", row["reasons"])

    def test_pending_operation_is_explicit(self):
        operations = [{"operationId": "P-1", "invoiceId": "INV-1", "amount": "100.00", "currency": "USD", "status": "PENDING"}]
        result = analyze_supplier_batch([invoice()], operations, policy=POLICY)
        row = result["rows"][0]
        self.assertEqual(row["operationState"], "PENDING")
        self.assertIn("PENDING_OPERATION", row["reasons"])

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
        operations = [operation()]
        result = analyze_supplier_batch([item], operations, policy=POLICY, observed_at="2026-11-08T12:00:00Z")
        self.assertNotIn("OVERDUE", result["rows"][0]["reasons"])

    def test_same_number_under_different_suppliers_requires_review(self):
        first = invoice(number="SHARED-1")
        second = invoice(invoice_id="INV-2", number="SHARED-1")
        second["supplier"] = "Different Supplier"
        result = analyze_supplier_batch([first, second], [], policy=POLICY)
        self.assertTrue(all("CONFLICTING_SUPPLIER_IDENTITY" in row["reasons"] for row in result["rows"]))
        self.assertEqual(result["metrics"]["reasonCounts"]["CONFLICTING_SUPPLIER_IDENTITY"], 2)

    def test_same_supplier_number_with_conflicting_facts_requires_review(self):
        first = invoice(number="CONFLICT-1", amount="100.00")
        second = invoice(invoice_id="INV-2", number="CONFLICT-1", amount="110.00")
        result = analyze_supplier_batch([first, second], [], policy=POLICY)
        self.assertTrue(all("CONFLICTING_INVOICE_FACTS" in row["reasons"] for row in result["rows"]))


if __name__ == "__main__":
    unittest.main()
