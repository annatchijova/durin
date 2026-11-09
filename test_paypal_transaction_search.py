import unittest
from datetime import datetime, timezone

from paypal_transaction_search import chunk_date_range, filter_transactions, normalize_transaction


def raw_transaction(txn_id, date, amount, email="supplier@example.com", subject="Invoice payment", note=""):
    return {
        "transaction_info": {
            "transaction_id": txn_id,
            "transaction_initiation_date": date,
            "transaction_updated_date": date,
            "transaction_amount": {"value": amount, "currency_code": "USD"},
            "transaction_status": "S",
            "transaction_event_code": "T0006",
            "transaction_subject": subject,
            "transaction_note": note,
            "invoice_id": f"INV-{txn_id}",
        },
        "payer_info": {"email_address": email, "payer_name": {"alternate_full_name": "Globex Supplies"}},
    }


class ChunkDateRangeTests(unittest.TestCase):
    def test_six_months_back_produces_bounded_chunks(self):
        now = datetime(2026, 11, 9, tzinfo=timezone.utc)
        chunks = chunk_date_range(months_back=6, now=now)
        self.assertGreaterEqual(len(chunks), 5)
        self.assertLessEqual(len(chunks), 7)
        # oldest first
        self.assertLess(chunks[0][0], chunks[-1][0])
        # each chunk is within PayPal's ~31 day limit
        for start, end in chunks:
            start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S-0000")
            end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S-0000")
            self.assertLessEqual((end_dt - start_dt).days, 31)

    def test_rejects_out_of_range_months(self):
        with self.assertRaises(ValueError):
            chunk_date_range(months_back=0)
        with self.assertRaises(ValueError):
            chunk_date_range(months_back=100)


class NormalizeTransactionTests(unittest.TestCase):
    def test_pulls_expected_fields(self):
        normalized = normalize_transaction(raw_transaction("T-1", "2026-05-01T00:00:00Z", "450.00"))
        self.assertEqual(normalized["transactionId"], "T-1")
        self.assertEqual(normalized["amountValue"], "450.00")
        self.assertEqual(normalized["counterpartyEmail"], "supplier@example.com")

    def test_missing_nested_keys_do_not_crash(self):
        normalized = normalize_transaction({})
        self.assertEqual(normalized["transactionId"], "")
        self.assertEqual(normalized["amountValue"], "")


class FilterTransactionsTests(unittest.TestCase):
    def setUp(self):
        self.transactions = [
            normalize_transaction(raw_transaction("T-1", "2026-05-01T00:00:00Z", "450.00", email="acme@paypal.com")),
            normalize_transaction(raw_transaction("T-2", "2026-08-01T00:00:00Z", "120.00", email="globex@paypal.com")),
            normalize_transaction(raw_transaction("T-3", "2026-06-15T00:00:00Z", "450.50", email="acme@paypal.com", subject="Consulting")),
        ]

    def test_amount_hint_matches_within_tolerance(self):
        result = filter_transactions(self.transactions, amount_hint="450.00")
        ids = {t["transactionId"] for t in result}
        self.assertIn("T-1", ids)
        self.assertIn("T-3", ids)  # within 2% tolerance
        self.assertNotIn("T-2", ids)

    def test_counterparty_hint_matches_email_or_name(self):
        result = filter_transactions(self.transactions, counterparty_hint="acme")
        ids = {t["transactionId"] for t in result}
        self.assertEqual(ids, {"T-1", "T-3"})

    def test_no_hints_returns_all_sorted_by_date_desc(self):
        result = filter_transactions(self.transactions)
        self.assertEqual([t["transactionId"] for t in result], ["T-2", "T-3", "T-1"])

    def test_unmatched_hint_returns_empty_not_a_guess(self):
        result = filter_transactions(self.transactions, counterparty_hint="nonexistent-company")
        self.assertEqual(result, [])

    def test_keywords_match_subject_or_invoice(self):
        result = filter_transactions(self.transactions, keywords=["Consulting"])
        self.assertEqual([t["transactionId"] for t in result], ["T-3"])


if __name__ == "__main__":
    unittest.main()
