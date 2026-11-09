import unittest

from contradiction_detection import detect_source_contradictions


def _invoice(invoice_id, source_id, **fields):
    defaults = {"supplier": "Acme Corp", "invoiceNumber": "INV-100", "recipient": "acme@paypal.com", "amount": "500.00", "currency": "USD", "dueDate": "2026-12-01", "concept": "services"}
    defaults.update(fields)
    provenance = {
        field: {"value": value, "provenance": {"sourceId": source_id, "sourceHash": f"hash-{source_id}", "evidenceExcerpt": f"excerpt-{field}"}}
        for field, value in defaults.items()
    }
    return {**defaults, "invoiceId": invoice_id, "provenance": provenance}


class CrossSourceContradictionTests(unittest.TestCase):
    def test_same_obligation_different_recipient_across_sources_is_flagged(self):
        invoices = [_invoice("source-a", "a", recipient="acme@paypal.com"), _invoice("source-b", "b", recipient="attacker@paypal.com")]
        findings = detect_source_contradictions(invoices)
        mismatches = [item for item in findings if item["type"] == "CROSS_SOURCE_FIELD_MISMATCH" and item["field"] == "recipient"]
        self.assertEqual(len(mismatches), 1)
        values = {item["value"] for item in mismatches[0]["observedValues"]}
        self.assertEqual(values, {"acme@paypal.com", "attacker@paypal.com"})

    def test_same_obligation_different_due_date_is_flagged(self):
        invoices = [_invoice("source-a", "a", dueDate="2026-12-01"), _invoice("source-b", "b", dueDate="2026-12-15")]
        findings = detect_source_contradictions(invoices)
        mismatches = [item for item in findings if item["field"] == "dueDate"]
        self.assertEqual(len(mismatches), 1)

    def test_same_values_from_two_sources_is_not_flagged(self):
        invoices = [_invoice("source-a", "a"), _invoice("source-b", "b")]
        findings = detect_source_contradictions(invoices)
        self.assertEqual(findings, [])

    def test_single_source_group_is_not_flagged(self):
        invoices = [_invoice("source-a", "a")]
        findings = detect_source_contradictions(invoices)
        self.assertEqual(findings, [])

    def test_amount_and_currency_are_not_duplicated_here(self):
        # supplier_operations.analyze_supplier_batch already raises
        # CONFLICTING_INVOICE_FACTS for amount/currency mismatches on the row;
        # this module must not re-flag the same disagreement a second time.
        invoices = [_invoice("source-a", "a", amount="500.00"), _invoice("source-b", "b", amount="450.00")]
        findings = detect_source_contradictions(invoices)
        self.assertEqual([item for item in findings if item["field"] in ("amount", "currency")], [])


if __name__ == "__main__":
    unittest.main()
