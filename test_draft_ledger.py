import tempfile
import unittest
from pathlib import Path

from draft_ledger import DraftLedger


class DraftLedgerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ledger = DraftLedger(Path(self._tmp.name) / "drafts.sqlite3")

    def tearDown(self):
        self._tmp.cleanup()

    def test_record_and_get_draft(self):
        self.ledger.record_draft(source_id="s1", source_hash="h" * 64, extractor_version="v1", candidate={"amount": "100.00"}, now="2026-11-08T00:00:00Z")
        draft = self.ledger.get("s1")
        self.assertEqual(draft["state"], "DRAFT")
        self.assertEqual(draft["candidate"]["amount"], "100.00")

    def test_draft_can_be_overwritten_while_still_draft(self):
        self.ledger.record_draft(source_id="s1", source_hash="h" * 64, extractor_version="v1", candidate={"amount": "100.00"}, now="t0")
        self.ledger.record_draft(source_id="s1", source_hash="h" * 64, extractor_version="v1", candidate={"amount": "200.00"}, now="t1")
        self.assertEqual(self.ledger.get("s1")["candidate"]["amount"], "200.00")

    def test_reviewed_draft_is_not_silently_re_extracted(self):
        self.ledger.record_draft(source_id="s1", source_hash="h" * 64, extractor_version="v1", candidate={"amount": "100.00"}, now="t0")
        self.ledger.set_review_state(source_id="s1", state="REVIEWED", review_note="confirmed by merchant", now="t1")
        with self.assertRaisesRegex(ValueError, "already REVIEWED"):
            self.ledger.record_draft(source_id="s1", source_hash="h" * 64, extractor_version="v1", candidate={"amount": "999.00"}, now="t2")

    def test_set_review_state_requires_existing_draft(self):
        with self.assertRaisesRegex(ValueError, "not recorded"):
            self.ledger.set_review_state(source_id="missing", state="REVIEWED", review_note=None, now="t0")

    def test_list_drafts_filters_by_state(self):
        self.ledger.record_draft(source_id="s1", source_hash="h" * 64, extractor_version="v1", candidate={}, now="t0")
        self.ledger.record_draft(source_id="s2", source_hash="h" * 64, extractor_version="v1", candidate={}, now="t0")
        self.ledger.set_review_state(source_id="s1", state="REJECTED", review_note="bad excerpt", now="t1")
        rejected = self.ledger.list_drafts(state="REJECTED")
        self.assertEqual([item["sourceId"] for item in rejected], ["s1"])
        drafts = self.ledger.list_drafts(state="DRAFT")
        self.assertEqual([item["sourceId"] for item in drafts], ["s2"])


if __name__ == "__main__":
    unittest.main()
