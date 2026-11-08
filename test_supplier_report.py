import json
import tempfile
import unittest
from pathlib import Path

from supplier_report import build_supplier_report, build_supplier_report_from_files, write_report


POLICY = {
    "merchantName": "Test Merchant",
    "baseCurrency": "USD",
    "maxAmountPerPayment": "1000.00",
    "maxAmountPerBatch": "2500.00",
    "approvalRequiredAbove": "0.00",
    "approvedRecipients": ["supplier@example.com"],
}
INVOICE = {
    "invoiceId": "INV-1",
    "supplier": "Acme",
    "invoiceNumber": "A-1",
    "recipient": "supplier@example.com",
    "amount": "100.00",
    "currency": "USD",
}


class SupplierReportTests(unittest.TestCase):
    def test_report_contains_payable_flow_and_provenance(self):
        report = build_supplier_report(
            policy=POLICY,
            invoices=[INVOICE],
            operations=[],
            source_manifest=[{"kind": "test", "source": "memory", "source_hash": "abc", "validation_status": "LOADED"}],
            report_id="R-1",
            observed_at="2026-11-08T12:00:00Z",
        )
        self.assertEqual(report["flow"], "PAYABLE")
        self.assertEqual(report["schemaVersion"], 1)
        self.assertEqual(report["metrics"]["invoiceCount"], 1)
        self.assertEqual(report["execution"], "NO_PAYMENT_SUBMITTED")

    def test_file_report_is_reproducible_for_same_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "policy.json").write_text(json.dumps(POLICY), encoding="utf-8")
            (root / "invoices.json").write_text(json.dumps([INVOICE]), encoding="utf-8")
            (root / "operations.json").write_text("[]", encoding="utf-8")
            first = build_supplier_report_from_files(
                policy_path=str(root / "policy.json"), invoices_path=str(root / "invoices.json"), operations_path=str(root / "operations.json"), report_id="R-1", observed_at="2026-11-08T12:00:00Z"
            )
            second = build_supplier_report_from_files(
                policy_path=str(root / "policy.json"), invoices_path=str(root / "invoices.json"), operations_path=str(root / "operations.json"), report_id="R-1", observed_at="2026-11-08T12:00:00Z"
            )
            self.assertEqual(first, second)

    def test_write_report_replaces_destination_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "reports" / "level1.json"
            write_report(destination, {"schemaVersion": 1, "ok": True})
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["ok"], True)


if __name__ == "__main__":
    unittest.main()
