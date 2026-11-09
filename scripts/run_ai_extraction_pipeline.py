#!/usr/bin/env python3
"""End-to-end AI extraction pipeline: sources -> OpenAI drafts -> validated report.

No frontend, no payment submission. This script:

1. Lists authorized sources from DURIN_SOURCE_DIR.
2. Calls OpenAI to produce one draft candidate per eligible source.
3. Records every draft in the durable draft ledger (DURIN_DRAFT_LEDGER_PATH)
   as DRAFT -- it is not yet reviewed or trusted.
4. Validates each draft's fields against the source content; an unsupported
   excerpt or hallucinated value is rejected at this boundary, not trusted.
5. Builds the deterministic supplier report, including cross-source and
   policy contradictions, so a merchant knows what needs review before any
   payout proposal is prepared.

OpenAI never approves anything and is never on the decision path: every value
it proposes is re-checked against the literal source text before it reaches
the report.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from draft_ledger import DraftLedger
from openai_extractor import OpenAIExtractionClient, OpenAIExtractionConfig, OpenAIProviderError
from source_ingestion import SUPPORTED_EXTRACTION_KINDS, list_sources
from source_workflow import build_report_from_extractions


EXTRACTOR_VERSION = "openai-extractor-v1"


def _load_json(path: str) -> list[dict[str, object]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def main() -> int:
    source_dir = os.environ.get("DURIN_SOURCE_DIR")
    if not source_dir:
        print(json.dumps({"ok": False, "error": "DURIN_SOURCE_DIR is not configured"}))
        return 2

    ledger = DraftLedger.from_env()
    if ledger is None:
        print(json.dumps({"ok": False, "error": "DURIN_DRAFT_LEDGER_PATH is required"}))
        return 2

    policy_raw = os.environ.get("DURIN_POLICY_JSON")
    if not policy_raw:
        print(json.dumps({"ok": False, "error": "DURIN_POLICY_JSON is not configured"}))
        return 2
    policy = json.loads(policy_raw)

    operations_path = os.environ.get("DURIN_OPERATIONS_PATH")
    operations = _load_json(operations_path) if operations_path else []

    client = OpenAIExtractionClient(OpenAIExtractionConfig.from_env())
    sources = list_sources(source_dir)
    eligible = [source for source in sources if source.get("kind") in SUPPORTED_EXTRACTION_KINDS and source.get("contentAvailable")]

    candidates_by_source_id: dict[str, dict[str, object]] = {}
    extraction_errors: list[dict[str, str]] = []
    now = datetime.now(timezone.utc).isoformat()
    for source in eligible:
        source_id = source["sourceId"]
        existing = ledger.get(source_id)
        if existing is not None and existing["state"] != "DRAFT":
            if existing["sourceHash"] == source["sourceHash"]:
                candidates_by_source_id[source_id] = existing["candidate"]
            continue
        try:
            candidate = client.extract_candidate(source_content=source["content"], source_kind=source["kind"])
        except (OpenAIProviderError, ValueError) as exc:
            extraction_errors.append({"sourceId": source_id, "source": source["source"], "error": str(exc)})
            continue
        ledger.record_draft(
            source_id=source_id,
            source_hash=source["sourceHash"],
            extractor_version=EXTRACTOR_VERSION,
            candidate=candidate,
            now=now,
        )
        candidates_by_source_id[source_id] = candidate

    report = build_report_from_extractions(
        policy=policy,
        sources=sources,
        candidates_by_source_id=candidates_by_source_id,
        operations=operations,
        report_id=os.environ.get("DURIN_REPORT_ID", f"ai-extraction-{now}"),
        observed_at=now,
        extractor_version=EXTRACTOR_VERSION,
    )
    print(json.dumps({"ok": True, "report": report, "extractionErrors": extraction_errors}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
