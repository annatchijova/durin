import unittest

from source_workflow import build_report_from_extractions


class SourceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            "sourceId": "source-1",
            "source": "/authorized/invoice-1.txt",
            "sourceHash": "hash-1",
            "content": "Supplier: Acme\nInvoice: A-1\nRecipient: supplier@example.com\nAmount: 100.00\nCurrency: USD\nDue: 2026-11-30\nConcept: Hosting",
            "requiresReview": False,
        }
        self.candidate = {
            "supplier": "Acme",
            "invoiceNumber": "A-1",
            "recipient": "supplier@example.com",
            "amount": "100.00",
            "currency": "USD",
            "dueDate": "2026-11-30",
            "concept": "Hosting",
            "evidence": {
                "supplier": "Supplier: Acme",
                "invoiceNumber": "Invoice: A-1",
                "recipient": "Recipient: supplier@example.com",
                "amount": "Amount: 100.00",
                "currency": "Currency: USD",
                "dueDate": "Due: 2026-11-30",
                "concept": "Concept: Hosting",
            },
        }
        self.policy = {
            "merchantName": "Merchant",
            "baseCurrency": "USD",
            "maxAmountPerPayment": "1000.00",
            "maxAmountPerBatch": "2500.00",
            "approvedRecipients": ["supplier@example.com"],
        }

    def test_source_to_report_preserves_provenance_and_metrics(self):
        report = build_report_from_extractions(
            policy=self.policy,
            sources=[self.source],
            candidates_by_source_id={"source-1": self.candidate},
            operations=[],
            report_id="R-1",
            observed_at="2026-11-08T12:00:00Z",
            extractor_version="test-extractor-1",
        )
        self.assertEqual(report["metrics"]["invoiceCount"], 1)
        self.assertEqual(report["extraction"]["extractedCount"], 1)
        self.assertEqual(report["rows"][0]["invoiceId"], "source-source-1")
        self.assertEqual(report["rows"][0]["status"], "READY_FOR_REVIEW")

    def test_missing_candidate_is_explicit_and_not_an_invoice(self):
        report = build_report_from_extractions(
            policy=self.policy,
            sources=[self.source],
            candidates_by_source_id={},
            operations=[],
            report_id="R-2",
            observed_at="2026-11-08T12:00:00Z",
            extractor_version="test-extractor-1",
        )
        self.assertEqual(report["metrics"]["invoiceCount"], 0)
        self.assertEqual(report["extraction"]["missingExtractionCount"], 1)
        self.assertEqual(report["sourceManifest"][0]["validationStatus"], "MISSING_EXTRACTION")


if __name__ == "__main__":
    unittest.main()
