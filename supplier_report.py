"""Canonical Level 1 supplier report construction and persistence."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from supplier_operations import analyze_supplier_batch


REPORT_SCHEMA_VERSION = 1
MAX_SOURCE_BYTES = 1_000_000


def canonical_bytes(value: Any) -> bytes:
    """Encode JSON with stable ordering for provenance hashes."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _read_json(path: str | os.PathLike[str]) -> Any:
    source = Path(path)
    if source.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError(f"source exceeds {MAX_SOURCE_BYTES} bytes: {source}")
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON source: {source}") from exc


def _source_entry(kind: str, path: str | os.PathLike[str], value: Any) -> dict[str, str]:
    return {
        "kind": kind,
        "source": str(path),
        "source_hash": sha256_json(value),
        "validation_status": "LOADED",
    }


def build_supplier_report(
    *,
    policy: dict[str, Any],
    invoices: list[dict[str, Any]],
    operations: list[dict[str, Any]],
    source_manifest: list[dict[str, str]],
    report_id: str,
    observed_at: str,
) -> dict[str, Any]:
    """Build a complete, review-only report from bounded source observations."""
    if not report_id or len(report_id) > 100:
        raise ValueError("report_id is required and bounded")
    if not observed_at or len(observed_at) > 64:
        raise ValueError("observed_at is required and bounded")
    if not isinstance(source_manifest, list) or not source_manifest:
        raise ValueError("source_manifest is required")
    analysis = analyze_supplier_batch(invoices, operations, policy=policy)
    return {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "reportId": report_id,
        "flow": "PAYABLE",
        "observedAt": observed_at,
        "policy": policy,
        "sourceManifest": source_manifest,
        "rows": analysis["rows"],
        "metrics": analysis["metrics"],
        "execution": analysis["execution"],
        "humanApprovalRequired": analysis["humanApprovalRequired"],
    }


def build_supplier_report_from_files(
    *,
    policy_path: str,
    invoices_path: str,
    operations_path: str,
    report_id: str,
    observed_at: str,
) -> dict[str, Any]:
    policy = _read_json(policy_path)
    invoices = _read_json(invoices_path)
    operations = _read_json(operations_path)
    if not isinstance(policy, dict) or not isinstance(invoices, list) or not isinstance(operations, list):
        raise ValueError("policy must be an object; invoices and operations must be arrays")
    manifest = [
        _source_entry("policy", policy_path, policy),
        _source_entry("invoices", invoices_path, invoices),
        _source_entry("operations", operations_path, operations),
    ]
    return build_supplier_report(
        policy=policy,
        invoices=invoices,
        operations=operations,
        source_manifest=manifest,
        report_id=report_id,
        observed_at=observed_at,
    )


def write_report(path: str | os.PathLike[str], report: dict[str, Any]) -> None:
    """Write a report atomically so a failed write cannot leave a false report."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    handle, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent, text=True)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
