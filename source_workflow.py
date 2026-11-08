"""Source-to-report orchestration for the merchant's AI extraction boundary."""

from __future__ import annotations

from typing import Any

from source_ingestion import validate_invoice_extraction
from supplier_report import build_supplier_report


def build_report_from_extractions(
    *,
    policy: dict[str, Any],
    sources: list[dict[str, Any]],
    candidates_by_source_id: dict[str, dict[str, Any]],
    operations: list[dict[str, Any]],
    report_id: str,
    observed_at: str,
    extractor_version: str,
) -> dict[str, Any]:
    """Turn AI candidates into a deterministic supplier report.

    The caller may use any model or agent to produce candidates. This function
    treats that output as untrusted data, validates every field against the
    source, and only then hands normalized invoices to the deterministic
    operations engine. It never lets a candidate choose policy, approve a
    payment, or assert that an operation was executed.
    """
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources must be a non-empty list")
    if not isinstance(candidates_by_source_id, dict):
        raise ValueError("candidates_by_source_id must be an object")
    invoices: list[dict[str, Any]] = []
    manifest: list[dict[str, str]] = []
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("sources must contain objects")
        source_id = source.get("sourceId")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("source is missing sourceId")
        candidate = candidates_by_source_id.get(source_id)
        if candidate is None:
            manifest.append(_manifest(source, "MISSING_EXTRACTION"))
            continue
        extracted = validate_invoice_extraction(
            source=source,
            candidate=candidate,
            extractor_version=extractor_version,
        )
        invoice = dict(extracted["invoice"])
        invoice["invoiceId"] = f"source-{source_id}"
        invoice["provenance"] = extracted["fields"]
        invoice["requiresReview"] = extracted["requiresReview"]
        invoices.append(invoice)
        manifest.append(_manifest(source, "EXTRACTED", extracted["requiresReview"]))
    report = build_supplier_report(
        policy=policy,
        invoices=invoices,
        operations=operations,
        source_manifest=manifest,
        report_id=report_id,
        observed_at=observed_at,
    )
    report["extraction"] = {
        "extractorVersion": extractor_version,
        "sourceCount": len(sources),
        "extractedCount": len(invoices),
        "missingExtractionCount": len(sources) - len(invoices),
        "requiresReviewCount": sum(bool(item.get("requiresReview")) for item in manifest),
    }
    return report


def _manifest(source: dict[str, Any], status: str, requires_review: bool = True) -> dict[str, str]:
    source_id = source.get("sourceId")
    source_hash = source.get("sourceHash")
    location = source.get("source")
    if not all(isinstance(value, str) and value for value in (source_id, source_hash, location)):
        raise ValueError("source provenance is incomplete")
    return {
        "sourceId": source_id,
        "source": location,
        "sourceHash": source_hash,
        "validationStatus": status,
        "requiresReview": str(bool(requires_review)).lower(),
    }
