import unittest

from operations_narrative import build_operations_report, explain_row


class OperationsNarrativeTests(unittest.TestCase):
    def test_narrative_cannot_hide_exception_reasons(self):
        result = explain_row({
            "invoiceId": "INV-1",
            "supplier": "Acme",
            "invoiceNumber": "A-1",
            "amount": "100.00",
            "currency": "USD",
            "status": "EXCLUDED",
            "operationState": "UNMATCHED",
            "reasons": ["POSSIBLE_DUPLICATE", "POSSIBLE_TYPO"],
        })
        self.assertEqual(result["reasons"], ["POSSIBLE_DUPLICATE", "POSSIBLE_TYPO"])
        self.assertIn("repeats", result["narrative"])
        self.assertIn("recipient", result["narrative"])

    def test_report_keeps_narrative_beside_fixed_analysis(self):
        result = build_operations_report({
            "rows": [{"invoiceId": "INV-1", "supplier": "Acme", "invoiceNumber": "A-1", "amount": "10.00", "currency": "USD", "status": "READY_FOR_REVIEW", "operationState": "UNMATCHED", "reasons": []}],
            "metrics": {"invoiceCount": 1, "readyCount": 1, "excludedCount": 0},
        })
        self.assertEqual(result["priorityInvoiceIds"], [])
        self.assertIn("fixed deterministic rows", result["narrativeBoundary"])


if __name__ == "__main__":
    unittest.main()
