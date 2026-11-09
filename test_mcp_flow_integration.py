"""End-to-end integration test for the agent-usable MCP flow.

Drives the actual mcp_server.* tool functions in the sequence an agent would
call them: list sources -> extract a draft per source (the agent's own model
call, outside the MCP boundary by design) -> validate and build the
deterministic report -> propose payment for the ready rows -> seal the
proposal. This is the same sequence confirmed live against the real OpenAI
API and the real PayPal Sandbox; here it runs offline with a fake extractor
so it stays in the regular test suite.
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import mcp_server


POLICY = json.dumps({
    "merchantName": "Durin MCP Flow Test",
    "baseCurrency": "USD",
    "maxAmountPerPayment": "100.00",
    "maxAmountPerBatch": "500.00",
    "approvalRequiredAbove": "0.00",
    "approvedRecipients": ["supplier@example.com"],
})


class FakeExtractionClient:
    def extract_candidate(self, *, source_content, source_kind):
        return {
            "supplier": "Globex Supplies",
            "invoiceNumber": "GLX-2026-001",
            "recipient": "supplier@example.com",
            "amount": "42.50",
            "currency": "USD",
            "dueDate": "2026-12-20",
            "concept": "Office supplies",
            "evidence": {
                "supplier": "Supplier: Globex Supplies",
                "invoiceNumber": "Invoice Number: GLX-2026-001",
                "recipient": "Recipient (PayPal): supplier@example.com",
                "amount": "Amount: 42.50 USD",
                "currency": "Amount: 42.50 USD",
                "dueDate": "Due Date: 2026-12-20",
                "concept": "Concept: Office supplies",
            },
        }


class MCPFlowIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        (Path(self.tempdir.name) / "invoice_clean.txt").write_text(
            "Supplier: Globex Supplies\nInvoice Number: GLX-2026-001\n"
            "Recipient (PayPal): supplier@example.com\nAmount: 42.50 USD\n"
            "Due Date: 2026-12-20\nConcept: Office supplies",
            encoding="utf-8",
        )
        self.env = patch.dict("os.environ", {"DURIN_POLICY_JSON": POLICY, "DURIN_SOURCE_DIR": self.tempdir.name}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tempdir.cleanup()

    def test_sources_to_sealed_proposal_through_the_mcp_tools_only(self):
        listed = mcp_server.list_sources()
        self.assertTrue(listed["ok"])
        self.assertTrue(listed["available"])
        sources = listed["sources"]
        self.assertEqual(len(sources), 1)

        client = FakeExtractionClient()
        candidates = {
            source["sourceId"]: client.extract_candidate(source_content=source["content"], source_kind=source["kind"])
            for source in sources
        }

        now = datetime.now(timezone.utc).isoformat()
        report_result = mcp_server.build_source_report(
            sources=sources, candidates_by_source_id=candidates, operations=[],
            report_id="mcp-flow-test-1", observed_at=now, extractor_version="fake-extractor-v1",
        )
        self.assertTrue(report_result["ok"])
        report = report_result["report"]
        self.assertEqual(report["extraction"]["extractedCount"], 1)
        self.assertEqual(report["contradictions"], [])

        ready_rows = [row for row in report["rows"] if row["status"] == "READY_FOR_REVIEW"]
        self.assertEqual(len(ready_rows), 1)

        proposal_result = mcp_server.create_payment_proposal(ready_rows)
        self.assertTrue(proposal_result["ok"])
        self.assertEqual(proposal_result["execution"], "NO_PAYMENT_SUBMITTED")
        self.assertTrue(proposal_result["humanApprovalRequired"])
        self.assertEqual(len(proposal_result["accepted"]), 1)

        created_at = datetime.now(timezone.utc)
        sealed = mcp_server.seal_payment_proposal(
            invoices=ready_rows,
            policy_version="mcp-flow-test-v1",
            evidence_refs=[f"source:{sources[0]['sourceId']}"],
            proposal_id="mcp-flow-test-proposal-1",
            created_at=created_at.isoformat(),
            expires_at=(created_at + timedelta(hours=1)).isoformat(),
        )
        self.assertTrue(sealed["ok"])
        self.assertEqual(sealed["proposal"]["status"], "PENDING_APPROVAL")
        self.assertEqual(sealed["proposal"]["execution"], "NO_PAYMENT_SUBMITTED")
        self.assertTrue(sealed["proposalDigest"])


if __name__ == "__main__":
    unittest.main()
