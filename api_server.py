"""HTTP bridge between the Durin frontend and the deterministic engine.

This is the only process that holds PayPal and OpenAI credentials. The
frontend never receives a credential, never calls PayPal or OpenAI directly,
and never decides a value on its own -- every endpoint here is a thin wrapper
around a function that already exists and is already tested without a web
server involved.

A "case" is one run of the pipeline, persisted as a JSON file so a page
reload does not lose it. It is not a database; it is the smallest durable
store that lets the frontend show a real journey instead of fabricating one.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


_load_dotenv(Path(__file__).resolve().parent / ".env")

from automation import prepare_proposal
from authorization import approve_proposal, create_immutable_proposal, proposal_digest
from draft_ledger import DraftLedger
from openai_extractor import OpenAIExtractionClient, OpenAIExtractionConfig, OpenAIProviderError
from paypal_client import PayPalProviderError, PayPalSandboxClient, PayPalSandboxConfig
from paypal_operation_adapter import operations_from_payout_response
from paypal_payouts import build_payout_request, normalize_payout_response
from source_ingestion import SUPPORTED_EXTRACTION_KINDS, list_sources
from source_workflow import build_report_from_extractions
from supplier_operations import analyze_supplier_batch


EXTRACTOR_VERSION = "openai-extractor-v1"
CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}$")


def _case_store_dir() -> Path:
    raw = os.environ.get("DURIN_CASE_STORE_DIR", "").strip() or str(Path(__file__).resolve().parent / ".local" / "cases")
    directory = Path(raw).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _case_path(report_id: str) -> Path:
    if not CASE_ID_RE.fullmatch(report_id):
        raise HTTPException(400, "invalid case id")
    return _case_store_dir() / f"{report_id}.json"


def _load_case(report_id: str) -> dict[str, Any]:
    path = _case_path(report_id)
    if not path.is_file():
        raise HTTPException(404, f"case not found: {report_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_case(case: dict[str, Any]) -> None:
    path = _case_path(case["reportId"])
    path.write_text(json.dumps(case, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_policy() -> dict[str, Any]:
    raw = os.environ.get("DURIN_POLICY_JSON", "")
    if not raw:
        raise HTTPException(500, "DURIN_POLICY_JSON is not configured")
    policy = json.loads(raw)
    if not isinstance(policy, dict):
        raise HTTPException(500, "DURIN_POLICY_JSON must be an object")
    return policy


app = FastAPI(title="Durin API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("DURIN_FRONTEND_ORIGIN", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunPipelineRequest(BaseModel):
    sourceDir: str | None = None


class ApproveRequest(BaseModel):
    approverId: str


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "paypalConfigured": bool(os.environ.get("PAYPAL_CLIENT_ID")), "openaiConfigured": bool(os.environ.get("OPENAI_API_KEY"))}


@app.get("/api/cases")
def list_cases() -> dict[str, Any]:
    cases = []
    for path in sorted(_case_store_dir().glob("*.json")):
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cases.append({
            "reportId": case["reportId"],
            "createdAt": case["createdAt"],
            "stage": case["stage"],
            "metrics": case["report"]["metrics"],
            "contradictionCount": len(case["report"].get("contradictions", [])),
        })
    cases.sort(key=lambda item: item["createdAt"], reverse=True)
    return {"cases": cases}


@app.get("/api/cases/{report_id}")
def get_case(report_id: str) -> dict[str, Any]:
    return _load_case(report_id)


@app.post("/api/pipeline/run")
def run_pipeline(request: RunPipelineRequest) -> dict[str, Any]:
    source_dir = request.sourceDir or os.environ.get("DURIN_SOURCE_DIR")
    if not source_dir:
        raise HTTPException(400, "sourceDir is required (or set DURIN_SOURCE_DIR)")
    policy = _load_policy()
    try:
        config = OpenAIExtractionConfig.from_env()
    except ValueError as exc:
        raise HTTPException(500, f"OpenAI is not configured: {exc}") from exc
    client = OpenAIExtractionClient(config)

    try:
        sources = list_sources(source_dir)
    except (OSError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    eligible = [source for source in sources if source.get("kind") in SUPPORTED_EXTRACTION_KINDS and source.get("contentAvailable")]
    if not eligible:
        raise HTTPException(400, "no eligible sources found in sourceDir")

    now = _now()
    ledger = DraftLedger.from_env()
    candidates: dict[str, dict[str, Any]] = {}
    extraction_errors = []
    for source in eligible:
        try:
            candidate = client.extract_candidate(source_content=source["content"], source_kind=source["kind"])
        except (OpenAIProviderError, ValueError) as exc:
            extraction_errors.append({"sourceId": source["sourceId"], "source": source["source"], "error": str(exc)})
            continue
        if ledger is not None:
            existing = ledger.get(source["sourceId"])
            if existing is None or existing["state"] == "DRAFT":
                ledger.record_draft(source_id=source["sourceId"], source_hash=source["sourceHash"], extractor_version=EXTRACTOR_VERSION, candidate=candidate, now=now)
        candidates[source["sourceId"]] = candidate

    report_id = f"case-{now.replace(':', '').replace('.', '').replace('+', 'z')}"
    report = build_report_from_extractions(
        policy=policy, sources=sources, candidates_by_source_id=candidates, operations=[],
        report_id=report_id, observed_at=now, extractor_version=EXTRACTOR_VERSION,
    )
    case = {
        "reportId": report_id, "createdAt": now, "stage": "EXTRACTED",
        "report": report, "extractionErrors": extraction_errors,
        "proposal": None, "proposalDigest": None, "authorization": None,
        "payoutRequest": None, "payoutResponse": None,
    }
    _save_case(case)
    return case


@app.post("/api/cases/{report_id}/proposal")
def create_proposal(report_id: str) -> dict[str, Any]:
    case = _load_case(report_id)
    policy = _load_policy()
    ready_rows = [row for row in case["report"]["rows"] if row["status"] == "READY_FOR_REVIEW"]
    if not ready_rows:
        raise HTTPException(400, "no rows are READY_FOR_REVIEW")
    try:
        proposal_preview = prepare_proposal(ready_rows, policy)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not proposal_preview["accepted"]:
        raise HTTPException(400, "no invoice is eligible for a proposal")
    now = _now()
    sealed = create_immutable_proposal(
        accepted=proposal_preview["accepted"], currency=proposal_preview["currency"],
        total_amount=proposal_preview["totalAmount"], policy_version=f"policy-{abs(hash(json.dumps(policy, sort_keys=True))) % 10_000}",
        evidence_refs=[row["invoiceId"] for row in ready_rows],
        proposal_id=f"{report_id}-proposal", created_at=now, expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    )
    case["proposal"] = sealed["proposal"]
    case["proposalDigest"] = sealed["proposalDigest"]
    case["stage"] = "PROPOSED"
    _save_case(case)
    return case


@app.post("/api/cases/{report_id}/approve")
def approve(report_id: str, request: ApproveRequest) -> dict[str, Any]:
    case = _load_case(report_id)
    if case["proposal"] is None:
        raise HTTPException(400, "no sealed proposal to approve")
    if not request.approverId.strip():
        raise HTTPException(400, "approverId is required")
    try:
        authorization = approve_proposal(
            proposal=case["proposal"], expected_digest=case["proposalDigest"],
            approver_id=request.approverId.strip(), approved_at=_now(),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    case["authorization"] = authorization
    case["stage"] = "APPROVED"
    _save_case(case)
    return case


@app.post("/api/cases/{report_id}/submit")
def submit_to_paypal(report_id: str) -> dict[str, Any]:
    case = _load_case(report_id)
    if case["authorization"] is None:
        raise HTTPException(400, "proposal is not approved")
    if case["payoutResponse"] is not None:
        raise HTTPException(400, "this case has already been submitted")
    payload = build_payout_request(
        proposal=case["proposal"], proposal_digest_value=case["proposalDigest"],
        authorization=case["authorization"], observed_at=_now(),
    )
    try:
        config = PayPalSandboxConfig.from_env()
    except ValueError as exc:
        raise HTTPException(500, f"PayPal is not configured: {exc}") from exc
    client = PayPalSandboxClient(config)
    try:
        response = client.create_payout(payload, payload["sender_batch_header"]["sender_batch_id"])
    except PayPalProviderError as exc:
        case["stage"] = "SUBMISSION_UNCERTAIN"
        case["payoutRequest"] = payload
        case["payoutError"] = {"status": exc.status, "body": exc.body}
        _save_case(case)
        raise HTTPException(502, f"PayPal rejected the payout: {exc}") from exc
    case["payoutRequest"] = payload
    case["payoutResponse"] = response
    case["stage"] = "SUBMITTED"
    _save_case(case)
    return _refresh_payout(case)


@app.post("/api/cases/{report_id}/refresh-payout")
def refresh_payout(report_id: str) -> dict[str, Any]:
    case = _load_case(report_id)
    if case["payoutResponse"] is None:
        raise HTTPException(400, "no payout has been submitted for this case")
    return _refresh_payout(case)


def _refresh_payout(case: dict[str, Any]) -> dict[str, Any]:
    batch_id = case["payoutResponse"]["batch_header"]["payout_batch_id"]
    config = PayPalSandboxConfig.from_env()
    client = PayPalSandboxClient(config)
    response = client.get_payout(batch_id)
    case["payoutResponse"] = response
    normalized = normalize_payout_response(response)
    case["normalizedPayout"] = normalized
    if response.get("items"):
        operations = operations_from_payout_response(response=response, request_payload=case["payoutRequest"])
        policy = _load_policy()
        ready_invoice_ids = {item["invoiceId"] for item in case["proposal"]["items"]}
        invoices = [row for row in case["report"]["rows"] if row["invoiceId"] in ready_invoice_ids]
        reconciled = analyze_supplier_batch(invoices, operations, policy=policy, observed_at=_now())
        case["reconciledRows"] = reconciled["rows"]
        case["stage"] = "RECONCILED"
    _save_case(case)
    return case


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
