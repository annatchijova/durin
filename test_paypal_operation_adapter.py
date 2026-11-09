import unittest

from paypal_operation_adapter import operations_from_payout_response
from supplier_operations import analyze_supplier_batch


def response_item(sender_item_id, *, receiver="supplier@example.com", amount="100.00", currency="USD", **overrides):
    # Mirrors the real PayPal Sandbox GET /v1/payments/payouts/{batch_id} shape:
    # sender_item_id, receiver, and amount are nested under payout_item; they are
    # never top-level fields on the response item.
    item = {
        "payout_item_id": "ITEM-1",
        "transaction_id": "TX-1",
        "transaction_status": "SUCCESS",
        "payout_item": {"sender_item_id": sender_item_id, "receiver": receiver, "amount": {"value": amount, "currency": currency}},
    }
    item.update(overrides)
    return item


class PayPalOperationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.request = {
            "sender_batch_header": {"sender_batch_id": "SENDER-BATCH-1"},
            "items": [{"sender_item_id": "INV-1", "receiver": "supplier@example.com", "amount": {"value": "100.00", "currency": "USD"}}],
        }

    def test_response_is_bound_to_sender_item_and_attested(self):
        response = {
            "batch_header": {"payout_batch_id": "PAYPAL-BATCH-1", "batch_status": "SUCCESS"},
            "items": [response_item("INV-1", payout_item_id="ITEM-1", transaction_id="TX-1")],
        }
        operations = operations_from_payout_response(response=response, request_payload=self.request)
        self.assertEqual(operations[0]["invoiceId"], "INV-1")
        self.assertEqual(operations[0]["providerEvidence"]["evidenceStatus"], "INTERPRETED")
        report = analyze_supplier_batch([{"invoiceId": "INV-1", "supplier": "Acme", "invoiceNumber": "A-1", "recipient": "supplier@example.com", "amount": "100.00", "currency": "USD"}], operations, policy={"baseCurrency": "USD", "approvedRecipients": ["supplier@example.com"], "maxAmountPerPayment": "1000.00"})
        self.assertEqual(report["rows"][0]["operationState"], "SUCCESS")

    def test_positional_or_unknown_items_are_rejected(self):
        response = {"batch_header": {"payout_batch_id": "B-1", "batch_status": "SUCCESS"}, "items": [response_item("OTHER", payout_item_id="I-1", transaction_id="T-1")]}
        with self.assertRaisesRegex(ValueError, "not present"):
            operations_from_payout_response(response=response, request_payload=self.request)

    def test_duplicate_response_items_are_rejected(self):
        item = response_item("INV-1", payout_item_id="I-1", transaction_id="T-1")
        second = response_item("INV-1", payout_item_id="I-2", transaction_id="T-2")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            operations_from_payout_response(response={"batch_header": {"payout_batch_id": "B-1", "batch_status": "SUCCESS"}, "items": [item, second]}, request_payload=self.request)

    def test_duplicate_provider_ids_and_batch_conflicts_are_rejected(self):
        first = response_item("INV-1", payout_item_id="I-1", transaction_id="T-1")
        duplicate = response_item("INV-2", payout_item_id="I-1", transaction_id="T-1")
        request = {**self.request, "items": [self.request["items"][0], {"sender_item_id": "INV-2", "receiver": "supplier2@example.com", "amount": {"value": "100.00", "currency": "USD"}}]}
        with self.assertRaisesRegex(ValueError, "duplicate provider"):
            operations_from_payout_response(response={"batch_header": {"payout_batch_id": "B-1", "batch_status": "SUCCESS"}, "items": [first, duplicate]}, request_payload=request)
        with self.assertRaisesRegex(ValueError, "conflicts"):
            operations_from_payout_response(response={"batch_header": {"payout_batch_id": "B-1", "batch_status": "DENIED"}, "items": [first]}, request_payload=self.request)

    def test_pending_item_without_transaction_id_is_bound_without_crashing(self):
        # Observed against the real PayPal Sandbox: a PENDING item has no
        # transaction_id until PayPal assigns one later.
        response = {
            "batch_header": {"payout_batch_id": "B-4", "batch_status": "PROCESSING"},
            "items": [response_item("INV-1", payout_item_id="ITEM-4", transaction_status="PENDING", transaction_id=None)],
        }
        operations = operations_from_payout_response(response=response, request_payload=self.request)
        self.assertEqual(operations[0]["operationId"], "ITEM-4")
        self.assertEqual(operations[0]["status"], "PENDING")

    def test_success_item_without_transaction_id_is_rejected(self):
        response = {
            "batch_header": {"payout_batch_id": "B-5", "batch_status": "SUCCESS"},
            "items": [response_item("INV-1", payout_item_id="ITEM-5", transaction_id=None)],
        }
        with self.assertRaisesRegex(ValueError, "transaction_id"):
            operations_from_payout_response(response=response, request_payload=self.request)

    def test_provider_receiver_must_match_approved_request(self):
        item = response_item("INV-1", payout_item_id="I-1", transaction_id="T-1", receiver="other@example.com")
        with self.assertRaisesRegex(ValueError, "receiver conflicts"):
            operations_from_payout_response(response={"batch_header": {"payout_batch_id": "B-1", "batch_status": "SUCCESS"}, "items": [item]}, request_payload=self.request)


if __name__ == "__main__":
    unittest.main()
