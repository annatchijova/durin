import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


POLICY = json.dumps({
    "merchantName": "Durin API Test",
    "baseCurrency": "USD",
    "maxAmountPerPayment": "100.00",
    "maxAmountPerBatch": "500.00",
    "approvalRequiredAbove": "0.00",
    "approvedRecipients": ["supplier@example.com"],
})


class FakeExtractionClient:
    def __init__(self, config=None):
        pass

    def extract_candidate(self, *, source_content, source_kind):
        return {
            "supplier": "Globex Supplies", "invoiceNumber": "GLX-1",
            "recipient": "supplier@example.com", "amount": "42.50", "currency": "USD",
            "dueDate": "2026-12-20", "concept": "Office supplies",
            "evidence": {
                "supplier": "Supplier: Globex Supplies", "invoiceNumber": "Invoice: GLX-1",
                "recipient": "Recipient: supplier@example.com", "amount": "Amount: 42.50 USD",
                "currency": "Amount: 42.50 USD", "dueDate": "Due: 2026-12-20", "concept": "Concept: Office supplies",
            },
        }


class APIServerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        (Path(self.tempdir.name) / "invoice.txt").write_text(
            "Supplier: Globex Supplies\nInvoice: GLX-1\nRecipient: supplier@example.com\n"
            "Amount: 42.50 USD\nDue: 2026-12-20\nConcept: Office supplies",
            encoding="utf-8",
        )
        self.case_store = tempfile.TemporaryDirectory()
        self.env = patch.dict("os.environ", {
            "DURIN_POLICY_JSON": POLICY,
            "DURIN_SOURCE_DIR": self.tempdir.name,
            "DURIN_CASE_STORE_DIR": self.case_store.name,
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://api.openai.com",
        }, clear=False)
        self.env.start()
        self.extraction_patch = patch("api_server.OpenAIExtractionClient", FakeExtractionClient)
        self.extraction_patch.start()
        import api_server
        self.client = TestClient(api_server.app)

    def tearDown(self):
        self.extraction_patch.stop()
        self.env.stop()
        self.tempdir.cleanup()
        self.case_store.cleanup()

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_pipeline_run_and_proposal_flow(self):
        run = self.client.post("/api/pipeline/run", json={})
        self.assertEqual(run.status_code, 200, run.text)
        case = run.json()
        self.assertEqual(case["stage"], "EXTRACTED")
        self.assertEqual(len(case["report"]["rows"]), 1)
        self.assertEqual(case["report"]["rows"][0]["status"], "READY_FOR_REVIEW")
        report_id = case["reportId"]

        listed = self.client.get("/api/cases")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["cases"]), 1)

        fetched = self.client.get(f"/api/cases/{report_id}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["reportId"], report_id)

        proposed = self.client.post(f"/api/cases/{report_id}/proposal")
        self.assertEqual(proposed.status_code, 200, proposed.text)
        proposed_case = proposed.json()
        self.assertEqual(proposed_case["stage"], "PROPOSED")
        self.assertEqual(proposed_case["proposal"]["status"], "PENDING_APPROVAL")

        approved = self.client.post(f"/api/cases/{report_id}/approve", json={"approverId": "merchant@example.com"})
        self.assertEqual(approved.status_code, 200, approved.text)
        approved_case = approved.json()
        self.assertEqual(approved_case["stage"], "APPROVED")
        self.assertEqual(approved_case["authorization"]["status"], "APPROVED")

    def test_approve_without_proposal_is_rejected(self):
        run = self.client.post("/api/pipeline/run", json={})
        report_id = run.json()["reportId"]
        response = self.client.post(f"/api/cases/{report_id}/approve", json={"approverId": "merchant@example.com"})
        self.assertEqual(response.status_code, 400)

    def test_unknown_case_is_404(self):
        response = self.client.get("/api/cases/does-not-exist")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
