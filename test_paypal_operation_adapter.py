import unittest

from paypal_operation_adapter import operations_from_payout_response
from supplier_operations import analyze_supplier_batch


class PayPalOperationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.request = {
            "sender_batch_header": {"sender_batch_id": "SENDER-BATCH-1"},
            "items": [{"sender_item_id": "INV-1", "receiver": "supplier@example.com", "amount": {"value": "100.00", "currency": "USD"}}],
        }

    def test_response_is_bound_to_sender_item_and_attested(self):
        response = {
            "batch_header": {"payout_batch_id": "PAYPAL-BATCH-1", "batch_status": "SUCCESS"},
            "items": [{"sender_item_id": "INV-1", "payout_item_id": "ITEM-1", "transaction_id": "TX-1", "transaction_status": "SUCCESS", "payout_item": {"receiver": "supplier@example.com", "amount": {"value": "100.00", "currency": "USD"}}}],
        }
        operations = operations_from_payout_response(response=response, request_payload=self.request)
        self.assertEqual(operations[0]["invoiceId"], "INV-1")
        self.assertEqual(operations[0]["providerEvidence"]["evidenceStatus"], "INTERPRETED")
        report = analyze_supplier_batch([{"invoiceId": "INV-1", "supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com", "amount": "100.00", "currency": "USD"}], operations, policy={"baseCurrency": "USD", "approvedRecipients": ["supplier@example.com"], "maxAmountPerPayment": "1000.00"})
        self.assertEqual(report["rows"][0]["operationState"], "SUCCESS")

    def test_positional_or_unknown_items_are_rejected(self):
        response = {"batch_header": {"payout_batch_id": "B-1", "batch_status": "SUCCESS"}, "items": [{"sender_item_id": "OTHER", "payout_item_id": "I-1", "transaction_id": "T-1", "transaction_status": "SUCCESS", "payout_item": {"receiver": "supplier@example.com", "amount": {"value": "100.00", "currency": "USD"}}}]}
        with self.assertRaisesRegex(ValueError, "not present"):
            operations_from_payout_response(response=response, request_payload=self.request)

    def test_duplicate_response_items_are_rejected(self):
        item = {"sender_item_id": "INV-1", "payout_item_id": "I-1", "transaction_id": "T-1", "transaction_status": "SUCCESS", "payout_item": {"receiver": "supplier@example.com", "amount": {"value": "100.00", "currency": "USD"}}}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            operations_from_payout_response(response={"batch_header": {"payout_batch_id": "B-1", "batch_status": "SUCCESS"}, "items": [item, dict(item, transaction_id="T-2", payout_item_id="I-2")]}, request_payload=self.request)

    def test_duplicate_provider_ids_and_batch_conflicts_are_rejected(self):
        first = {"sender_item_id": "INV-1", "payout_item_id": "I-1", "transaction_id": "T-1", "transaction_status": "SUCCESS", "payout_item": {"receiver": "supplier@example.com", "amount": {"value": "100.00", "currency": "USD"}}}
        duplicate = dict(first, sender_item_id="INV-2")
        request = {**self.request, "items": [self.request["items"][0], {"sender_item_id": "INV-2", "receiver": "supplier2@example.com", "amount": {"value": "100.00", "currency": "USD"}}]}
        with self.assertRaisesRegex(ValueError, "duplicate provider"):
            operations_from_payout_response(response={"batch_header": {"payout_batch_id": "B-1", "batch_status": "SUCCESS"}, "items": [first, duplicate]}, request_payload=request)
        with self.assertRaisesRegex(ValueError, "conflicts"):
            operations_from_payout_response(response={"batch_header": {"payout_batch_id": "B-1", "batch_status": "DENIED"}, "items": [first]}, request_payload=self.request)

    def test_provider_receiver_must_match_approved_request(self):
        item = {"sender_item_id": "INV-1", "payout_item_id": "I-1", "transaction_id": "T-1", "transaction_status": "SUCCESS", "payout_item": {"receiver": "other@example.com", "amount": {"value": "100.00", "currency": "USD"}}}
        with self.assertRaisesRegex(ValueError, "receiver conflicts"):
            operations_from_payout_response(response={"batch_header": {"payout_batch_id": "B-1", "batch_status": "SUCCESS"}, "items": [item]}, request_payload=self.request)


if __name__ == "__main__":
    unittest.main()
