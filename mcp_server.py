"""Durin's bounded MCP surface for merchant payment preparation.

The server reads untrusted invoice data, applies a merchant policy, and returns
an explainable proposal. It has no payment, capture, credential, or signing tool.
The eventual PayPal adapter will live behind the explicit merchant approval step.
"""

from __future__ import annotations

import json
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from automation import prepare_proposal
from source_ingestion import list_sources as ingest_sources, validate_invoice_extraction
from supplier_operations import analyze_supplier_batch
from operations_narrative import build_operations_report


mcp = FastMCP("durin-merchant-automation")

MAX_POLICY_BYTES = 64_000
MAX_INVOICE_FILE_BYTES = 1_000_000
MAX_INVOICES = 500
MAX_FIELD_LENGTH = 256
MAX_DECIMAL_DIGITS = 40
INVOICE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,99}$")


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": code, "message": message, **extra}


def _text(value: Any, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if len(value) > MAX_FIELD_LENGTH:
        raise ValueError(f"{field} exceeds the length limit")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    return value


def _amount(value: Any, field: str = "amount", *, allow_zero: bool = False) -> Decimal:
    raw = _text(value, field)
    if len(raw) > MAX_DECIMAL_DIGITS or not re.fullmatch(r"\d+(?:\.\d{1,4})?", raw):
        raise ValueError(f"{field} must be a positive decimal amount")
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{field} is not a valid decimal amount") from exc
    if parsed < 0 or (parsed == 0 and not allow_zero):
        raise ValueError(f"{field} must be {'non-negative' if allow_zero else 'greater than zero'}")
    return parsed


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def _distance_one_or_two(left: str, right: str) -> int | None:
    if len(left) != len(right):
        return None
    distance = sum(a != b for a, b in zip(left.casefold(), right.casefold()))
    return distance if 1 <= distance <= 2 else None


def _load_policy() -> dict[str, Any]:
    raw = os.environ.get("DURIN_POLICY_JSON", "")
    if len(raw.encode("utf-8")) > MAX_POLICY_BYTES:
        raise ValueError("DURIN_POLICY_JSON exceeds the size limit")
    if not raw:
        return {
            "merchantName": "Demo merchant",
            "baseCurrency": "USD",
            "maxAmountPerPayment": "10000.00",
            "maxAmountPerBatch": "50000.00",
            "approvalRequiredAbove": "0.00",
            "approvedRecipients": [],
        }
    policy = json.loads(raw)
    if not isinstance(policy, dict):
        raise ValueError("DURIN_POLICY_JSON must contain an object")
    normalized = {
        "merchantName": _text(policy.get("merchantName", "Merchant"), "merchantName"),
        "baseCurrency": _text(policy.get("baseCurrency", "USD"), "baseCurrency").upper(),
        "maxAmountPerPayment": _money(_amount(policy.get("maxAmountPerPayment", "10000.00"), "maxAmountPerPayment")),
        "maxAmountPerBatch": _money(_amount(policy.get("maxAmountPerBatch", "50000.00"), "maxAmountPerBatch")),
        "approvalRequiredAbove": _money(_amount(policy.get("approvalRequiredAbove", "0.00"), "approvalRequiredAbove", allow_zero=True)),
        "approvedRecipients": [],
    }
    recipients = policy.get("approvedRecipients", [])
    if not isinstance(recipients, list) or len(recipients) > MAX_INVOICES:
        raise ValueError("approvedRecipients must be a bounded array")
    normalized["approvedRecipients"] = [_text(item, "approved recipient") for item in recipients]
    if Decimal(normalized["approvalRequiredAbove"]) > Decimal(normalized["maxAmountPerPayment"]):
        raise ValueError("approvalRequiredAbove cannot exceed maxAmountPerPayment")
    if Decimal(normalized["maxAmountPerPayment"]) > Decimal(normalized["maxAmountPerBatch"]):
        raise ValueError("maxAmountPerPayment cannot exceed maxAmountPerBatch")
    return normalized


def _invoice_identity(invoice: dict[str, Any]) -> tuple[str, str, str, str]:
    supplier = _text(invoice.get("supplier"), "supplier").casefold()
    number = _text(invoice.get("invoiceNumber"), "invoiceNumber").casefold()
    currency = _text(invoice.get("currency", "USD"), "currency").upper()
    amount = _money(_amount(invoice.get("amount")))
    return supplier, number, currency, amount


@mcp.tool()
def get_agent_capabilities() -> dict[str, Any]:
    """Describe the bounded capabilities exposed to an agent."""
    return {
        "ok": True,
        "agent": "durin-merchant-automation",
        "can": ["read_sources", "read_policy", "read_invoices", "extract_invoice_facts", "find_duplicates", "analyze_supplier_operations", "generate_operations_report", "prepare_payment_proposal"],
        "cannot": ["approve_payment", "capture_payment", "send_money", "read_secrets"],
        "approvalBoundary": "A merchant must explicitly authorize any payment action.",
    }


@mcp.tool()
def get_business_policy() -> dict[str, Any]:
    """Return the merchant policy without exposing credentials."""
    try:
        return {"ok": True, "policy": _load_policy()}
    except (ValueError, json.JSONDecodeError) as exc:
        return _error("invalid_policy", str(exc))


@mcp.tool()
def list_invoices() -> dict[str, Any]:
    """Load optional local invoice observations; missing data is explicit."""
    path_value = os.environ.get("DURIN_INVOICES_PATH")
    if not path_value:
        return {"ok": True, "available": False, "invoices": [], "reason": "DURIN_INVOICES_PATH is not configured"}
    path = Path(path_value).expanduser()
    try:
        if path.stat().st_size > MAX_INVOICE_FILE_BYTES:
            return _error("invalid_invoices", "invoice fixture exceeds the byte limit")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or len(data) > MAX_INVOICES:
            return _error("invalid_invoices", "invoice fixture must be a bounded JSON array")
        return {"ok": True, "available": True, "invoices": data}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _error("invalid_invoices", str(exc))


@mcp.tool()
def list_sources() -> dict[str, Any]:
    """List authorized source files with hashes and bounded content."""
    root = os.environ.get("DURIN_SOURCE_DIR")
    if not root:
        return {"ok": True, "available": False, "sources": [], "reason": "DURIN_SOURCE_DIR is not configured"}
    try:
        return {"ok": True, "available": True, "sources": ingest_sources(root)}
    except (OSError, ValueError) as exc:
        return _error("source_listing_failed", str(exc))


@mcp.tool()
def extract_invoice_facts(source: dict[str, Any], candidate: dict[str, Any], extractor_version: str) -> dict[str, Any]:
    """Validate AI-extracted invoice facts and attach source-controlled provenance."""
    try:
        return {"ok": True, **validate_invoice_extraction(source=source, candidate=candidate, extractor_version=extractor_version)}
    except (ValueError, TypeError, KeyError) as exc:
        return _error("extraction_validation_failed", str(exc))


@mcp.tool()
def find_possible_duplicates(invoices: list[dict[str, Any]]) -> dict[str, Any]:
    """Find repeated invoice identities without deciding whether they are fraud."""
    if not isinstance(invoices, list) or len(invoices) > MAX_INVOICES:
        return _error("duplicate_check_failed", "invoices must be a bounded array")
    groups: dict[tuple[str, str, str, str], list[str]] = {}
    try:
        for index, invoice in enumerate(invoices):
            if not isinstance(invoice, dict):
                return _error("duplicate_check_failed", f"invoice {index} must be an object")
            invoice_id = _text(invoice.get("invoiceId", f"row-{index}"), "invoiceId")
            groups.setdefault(_invoice_identity(invoice), []).append(invoice_id)
    except ValueError as exc:
        return _error("duplicate_check_failed", str(exc))
    duplicates = [{"identity": list(identity), "invoiceIds": ids} for identity, ids in groups.items() if len(ids) > 1]
    return {"ok": True, "duplicates": duplicates, "duplicateCount": sum(len(item["invoiceIds"]) for item in duplicates)}


@mcp.tool()
def create_payment_proposal(invoices: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the pure automation engine's review-only payment proposal."""
    try:
        policy = _load_policy()
        proposal = prepare_proposal(invoices, policy)
        return {"ok": True, "merchant": policy["merchantName"], **proposal}
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return _error("proposal_failed", str(exc))


@mcp.tool()
def analyze_supplier_operations(
    invoices: list[dict[str, Any]], operations: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Run supplier preflight, conflict detection, and exact batch metrics."""
    try:
        result = analyze_supplier_batch(invoices, operations or [], policy=_load_policy())
        return {"ok": True, **result}
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return _error("operations_analysis_failed", str(exc))


@mcp.tool()
def generate_operations_report(
    invoices: list[dict[str, Any]], operations: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Return deterministic supplier metrics plus a separate explanation layer."""
    try:
        analysis = analyze_supplier_batch(invoices, operations or [], policy=_load_policy())
        return {"ok": True, "analysis": analysis, "report": build_operations_report(analysis)}
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return _error("operations_report_failed", str(exc))


if __name__ == "__main__":
    mcp.run()
