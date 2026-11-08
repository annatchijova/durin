import unittest

from paypal_reconciliation import preserve_provider_evidence, provider_request_id, reconcile_provider_evidence


class PayPalReconciliationTests(unittest.TestCase):
    def test_provider_key_is_stable_and_scoped(self):
        first = provider_request_id("merchant-a", "request-1")
        self.assertEqual(first, provider_request_id("merchant-a", "request-1"))
        self.assertNotEqual(first, provider_request_id("merchant-b", "request-1"))

    def test_uninterpretable_provider_amount_is_preserved(self):
        evidence = preserve_provider_evidence({
            "payout_item_id": "ITEM-1", "transaction_status": "SUCCESS",
            "payout_item": {"amount": {"value": "5.001", "currency": "USD"}},
        })
        self.assertEqual(evidence["providerAmountValue"], "5.001")
        self.assertEqual(evidence["evidenceStatus"], "REQUIRES_RECONCILIATION")
        self.assertEqual(reconcile_provider_evidence(expected_amount="5.00", expected_currency="USD", evidence=evidence)["status"], "RECONCILIATION_REQUIRED")

    def test_exact_success_is_the_only_match(self):
        evidence = preserve_provider_evidence({
            "transaction_id": "TX-1", "transaction_status": "SUCCESS",
            "payout_item": {"amount": {"value": "5.00", "currency": "USD"}},
        })
        self.assertEqual(reconcile_provider_evidence(expected_amount="5.00", expected_currency="USD", evidence=evidence)["status"], "MATCHED")

    def test_currency_or_amount_mismatch_is_not_posted(self):
        evidence = preserve_provider_evidence({
            "transaction_status": "SUCCESS",
            "payout_item": {"amount": {"value": "6.00", "currency": "USD"}},
        })
        result = reconcile_provider_evidence(expected_amount="5.00", expected_currency="USD", evidence=evidence)
        self.assertEqual(result, {"status": "RECONCILIATION_REQUIRED", "reason": "AMOUNT_OR_CURRENCY_MISMATCH"})


if __name__ == "__main__":
    unittest.main()
