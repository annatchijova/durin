import tempfile
import unittest
from pathlib import Path

from source_ingestion import list_sources
from source_workflow import build_report_from_extractions


class SourceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        source_path = Path(self.tempdir.name) / "invoice-1.txt"
        source_path.write_text("Supplier: Acme\nInvoice: A-1\nRecipient: supplier@example.com\nAmount: 100.00\nCurrency: USD\nDue: 2026-11-30\nConcept: Hosting", encoding="utf-8")
        self.source = list_sources(self.tempdir.name)[0]
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

    def tearDown(self):
        self.tempdir.cleanup()

    def test_source_to_report_preserves_provenance_and_metrics(self):
        report = build_report_from_extractions(
            policy=self.policy,
            sources=[self.source],
            candidates_by_source_id={self.source["sourceId"]: self.candidate},
            operations=[],
            report_id="R-1",
            observed_at="2026-11-08T12:00:00Z",
            extractor_version="test-extractor-1",
        )
        self.assertEqual(report["metrics"]["invoiceCount"], 1)
        self.assertEqual(report["extraction"]["extractedCount"], 1)
        self.assertEqual(report["rows"][0]["invoiceId"], f"source-{self.source['sourceId']}")
        self.assertEqual(report["rows"][0]["status"], "READY_FOR_REVIEW")
        self.assertEqual(len(report["extractedInvoices"]), 1)
        self.assertIn("provenance", report["extractedInvoices"][0])
        self.assertIn("amount", report["extractedInvoices"][0]["provenance"])

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

    def test_malformed_candidate_is_rejected_without_destroying_the_batch(self):
        second_path = Path(self.tempdir.name) / "invoice-2.txt"
        second_path.write_text("Supplier: Beta\nInvoice: B-1\nRecipient: beta@example.com\nAmount: 50.00\nCurrency: USD\nDue: 2026-11-30\nConcept: Hosting", encoding="utf-8")
        both_sources = list_sources(self.tempdir.name)
        second_source = next(item for item in both_sources if item["source"] == str(second_path))
        self.source = next(item for item in both_sources if item["source"] != str(second_path))
        malformed = dict(self.candidate)
        malformed["amount"] = "500.00 USD"  # not a bare decimal; must be rejected, not crash the batch
        report = build_report_from_extractions(
            policy=self.policy,
            sources=[self.source, second_source],
            candidates_by_source_id={self.source["sourceId"]: malformed, second_source["sourceId"]: self.candidate},
            operations=[],
            report_id="R-3",
            observed_at="2026-11-08T12:00:00Z",
            extractor_version="test-extractor-1",
        )
        self.assertEqual(report["extraction"]["extractedCount"], 1)
        self.assertEqual(report["extraction"]["rejectedExtractionCount"], 1)
        rejected = [item for item in report["sourceManifest"] if item["validationStatus"] == "EXTRACTION_REJECTED"]
        self.assertEqual(len(rejected), 1)
        self.assertIn("rejectionReason", rejected[0])


if __name__ == "__main__":
    unittest.main()
