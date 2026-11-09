import unittest

from paypal_report_workflow import build_paypal_supplier_report


class PayPalReportWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.invoices = [{
            "invoiceId": "INV-1", "supplier": "Acme", "invoiceNumber": "A-1",
            "recipient": "supplier@example.com", "amount": "100.00", "currency": "USD",
        }]
        self.policy = {
            "baseCurrency": "USD", "approvedRecipients": ["supplier@example.com"],
            "maxAmountPerPayment": "1000.00",
        }
        self.request = {
            "sender_batch_header": {"sender_batch_id": "SENDER-1"},
            "items": [{"sender_item_id": "INV-1", "receiver": "supplier@example.com", "amount": {"value": "100.00", "currency": "USD"}}],
        }

    def test_provider_response_updates_report_without_network(self):
        response = {
            "batch_header": {"payout_batch_id": "BATCH-1", "batch_status": "SUCCESS"},
            "items": [{"sender_item_id": "INV-1", "payout_item_id": "ITEM-1", "transaction_id": "TX-1", "transaction_status": "SUCCESS", "payout_item": {"receiver": "supplier@example.com", "amount": {"value": "100.00", "currency": "USD"}}}],
        }
        report = build_paypal_supplier_report(invoices=self.invoices, policy=self.policy, request_payload=self.request, provider_response=response, report_id="R-1", observed_at="2026-11-08T12:00:00Z")
        self.assertEqual(report["reportId"], "R-1")
        self.assertEqual(report["rows"][0]["operationState"], "SUCCESS")
        self.assertEqual(report["paypal"]["payoutBatchId"], "BATCH-1")

    def test_pending_provider_state_remains_explicit(self):
        response = {
            "batch_header": {"payout_batch_id": "BATCH-2", "batch_status": "PENDING"},
            "items": [{"sender_item_id": "INV-1", "payout_item_id": "ITEM-2", "transaction_id": "TX-2", "transaction_status": "PENDING", "payout_item": {"receiver": "supplier@example.com", "amount": {"value": "100.00", "currency": "USD"}}}],
        }
        report = build_paypal_supplier_report(invoices=self.invoices, policy=self.policy, request_payload=self.request, provider_response=response, report_id="R-2", observed_at="2026-11-08T12:00:00Z")
        self.assertEqual(report["rows"][0]["operationState"], "PENDING")
        self.assertIn("PENDING_OPERATION", report["rows"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
