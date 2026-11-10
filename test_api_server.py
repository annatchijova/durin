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
        summary = listed.json()["cases"][0]
        self.assertEqual(summary["suppliers"], sorted({row["supplier"] for row in case["report"]["rows"]}))
        self.assertEqual(summary["identityConflictCount"], 0)

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


class FakeChatClient:
    def __init__(self, extraction_client=None):
        pass

    def interpret_query(self, question):
        return {"monthsBack": 1, "counterpartyHint": "acme", "amountHint": None, "keywords": []}

    def narrate_results(self, *, question, transactions):
        if not transactions:
            return "No matching payment was found in the searched period."
        txn = transactions[0]
        return f"Found {txn['transactionId']} for {txn['amountValue']} {txn['currency']} on {txn['date']}."


class FakePayPalSearchClient:
    def __init__(self, config=None):
        pass

    def search_transactions(self, *, start_date, end_date, page=1, page_size=100):
        if page > 1:
            return {"transaction_details": [], "total_pages": 1}
        return {
            "transaction_details": [
                {
                    "transaction_info": {
                        "transaction_id": "TXN-ACME-1",
                        "transaction_initiation_date": "2026-05-01T00:00:00Z",
                        "transaction_amount": {"value": "450.00", "currency_code": "USD"},
                        "transaction_status": "S",
                    },
                    "payer_info": {"email_address": "acme@paypal.com", "payer_name": {"alternate_full_name": "Acme Corp"}},
                }
            ],
            "total_pages": 1,
        }


class ChatEndpointTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://api.openai.com",
            "PAYPAL_CLIENT_ID": "id",
            "PAYPAL_CLIENT_SECRET": "secret",
            "PAYPAL_BASE_URL": "https://api-m.sandbox.paypal.com",
        }, clear=False)
        self.env.start()
        self.chat_patch = patch("api_server.OpenAIChatClient", FakeChatClient)
        self.chat_patch.start()
        self.paypal_patch = patch("api_server.PayPalSandboxClient", FakePayPalSearchClient)
        self.paypal_patch.start()
        import api_server
        self.client = TestClient(api_server.app)

    def tearDown(self):
        self.paypal_patch.stop()
        self.chat_patch.stop()
        self.env.stop()

    def test_chat_finds_and_narrates_a_real_matching_transaction(self):
        response = self.client.post("/api/chat", json={"question": "Did we pay Acme 450 recently?"})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(len(body["transactions"]), 1)
        self.assertEqual(body["transactions"][0]["transactionId"], "TXN-ACME-1")
        self.assertIn("TXN-ACME-1", body["answer"])

    def test_chat_with_no_match_still_returns_an_honest_answer(self):
        with patch("api_server.OpenAIChatClient", FakeChatClient):
            class NoMatchChat(FakeChatClient):
                def interpret_query(self, question):
                    return {"monthsBack": 1, "counterpartyHint": "nonexistent-corp", "amountHint": None, "keywords": []}

            with patch("api_server.OpenAIChatClient", NoMatchChat):
                response = self.client.post("/api/chat", json={"question": "Did we pay Nonexistent Corp?"})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["transactions"], [])
        self.assertIn("No matching", body["answer"])


class PolicyLoadingTests(unittest.TestCase):
    """_load_policy accepts inline JSON or a file path and never invents a default."""

    def test_missing_policy_is_a_configuration_error(self):
        import api_server
        from fastapi import HTTPException
        with patch.dict("os.environ", {"DURIN_POLICY_JSON": "", "DURIN_POLICY_PATH": ""}, clear=False):
            with self.assertRaises(HTTPException) as raised:
                api_server._load_policy()
        self.assertEqual(raised.exception.status_code, 500)
        self.assertIn("DURIN_POLICY_PATH", raised.exception.detail)

    def test_policy_path_relative_to_repo_root(self):
        import api_server
        with patch.dict("os.environ", {"DURIN_POLICY_JSON": "", "DURIN_POLICY_PATH": "examples/level1/policy.json"}, clear=False):
            policy = api_server._load_policy()
        self.assertEqual(policy["merchantName"], "Durin Demo Merchant")

    def test_inline_json_wins_over_path(self):
        import api_server
        with patch.dict("os.environ", {"DURIN_POLICY_JSON": POLICY, "DURIN_POLICY_PATH": "examples/level1/policy.json"}, clear=False):
            policy = api_server._load_policy()
        self.assertEqual(policy["merchantName"], "Durin API Test")

    def test_policy_path_to_missing_file_is_reported(self):
        import api_server
        from fastapi import HTTPException
        with patch.dict("os.environ", {"DURIN_POLICY_JSON": "", "DURIN_POLICY_PATH": "examples/does-not-exist.json"}, clear=False):
            with self.assertRaises(HTTPException) as raised:
                api_server._load_policy()
        self.assertIn("does not point to a file", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
