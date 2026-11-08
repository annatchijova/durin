"""Bounded source ingestion and provenance-preserving extraction validation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


MAX_SOURCE_BYTES = 2_000_000
MAX_SOURCES = 100
MAX_CONTENT_CHARS = 200_000
TEXT_SUFFIXES = {".eml", ".txt", ".md", ".csv", ".json"}
ALLOWED_INVOICE_FIELDS = {
    "supplier",
    "invoiceNumber",
    "recipient",
    "amount",
    "currency",
    "dueDate",
    "concept",
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _kind(path: Path) -> str:
    name = path.name.casefold()
    if path.suffix.casefold() == ".eml" or "mail" in name or "email" in name:
        return "EMAIL"
    if "contract" in name or "agreement" in name:
        return "CONTRACT"
    if "invoice" in name or "factura" in name:
        return "INVOICE"
    return "DOCUMENT"


def _read_source(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError(f"source exceeds {MAX_SOURCE_BYTES} bytes: {path.name}")
    digest = _sha256(raw)
    source = {
        "sourceId": digest[:24],
        "source": str(path),
        "kind": _kind(path),
        "sourceHash": digest,
        "sizeBytes": len(raw),
        "contentAvailable": path.suffix.casefold() in TEXT_SUFFIXES,
        "validationStatus": "LOADED",
        "requiresReview": False,
    }
    if source["contentAvailable"]:
        content = raw.decode("utf-8", errors="replace")
        if len(content) > MAX_CONTENT_CHARS:
            source["content"] = content[:MAX_CONTENT_CHARS]
            source["requiresReview"] = True
            source["validationStatus"] = "TRUNCATED"
        else:
            source["content"] = content
    else:
        source["validationStatus"] = "METADATA_ONLY"
        source["requiresReview"] = True
    return source


def list_sources(root: str | os.PathLike[str]) -> list[dict[str, Any]]:
    """List regular, non-symlink sources in a bounded directory tree."""
    directory = Path(root).expanduser()
    if not directory.is_dir():
        raise ValueError("source directory does not exist")
    paths = sorted(path for path in directory.rglob("*") if path.is_file() and not path.is_symlink())
    if len(paths) > MAX_SOURCES:
        raise ValueError("source directory exceeds the item limit")
    return [_read_source(path) for path in paths]


def validate_invoice_extraction(
    *,
    source: dict[str, Any],
    candidate: dict[str, Any],
    extractor_version: str,
) -> dict[str, Any]:
    """Validate model output and attach source-controlled provenance.

    The candidate is data from an untrusted extractor. The source hash and
    provenance fields are always taken from the ingested source, never from the
    candidate itself.
    """
    if not isinstance(candidate, dict):
        raise ValueError("extraction candidate must be an object")
    unexpected = set(candidate) - (ALLOWED_INVOICE_FIELDS | {"evidence"})
    if unexpected:
        raise ValueError(f"extraction contains unauthorized fields: {sorted(unexpected)}")
    missing = ALLOWED_INVOICE_FIELDS - set(candidate)
    if missing:
        raise ValueError(f"extraction is missing fields: {sorted(missing)}")
    if not source.get("sourceId") or not source.get("sourceHash"):
        raise ValueError("source provenance is incomplete")
    evidence = candidate.get("evidence", {})
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    content = str(source.get("content", ""))
    fields: dict[str, Any] = {}
    for field in sorted(ALLOWED_INVOICE_FIELDS):
        value = candidate[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise ValueError(f"extracted field is invalid: {field}")
        excerpt = evidence.get(field, "")
        excerpt_is_supported = isinstance(excerpt, str) and bool(excerpt) and excerpt in content
        fields[field] = {
            "value": value.strip(),
            "provenance": {
                "source": source["source"],
                "sourceHash": source["sourceHash"],
                "sourceId": source["sourceId"],
                "fieldName": field,
                "evidenceExcerpt": excerpt if isinstance(excerpt, str) else "",
                "observedAt": source.get("observedAt"),
                "extractionMethod": "AI_STRUCTURED_EXTRACTION",
                "extractorVersion": extractor_version,
                "confidenceSignal": "UNSPECIFIED",
                "validationStatus": "SUPPORTED" if excerpt_is_supported else "UNSUPPORTED_EVIDENCE",
                "requiresReview": not excerpt_is_supported or bool(source.get("requiresReview")),
            },
        }
    return {
        "sourceId": source["sourceId"],
        "sourceHash": source["sourceHash"],
        "invoice": {field: fields[field]["value"] for field in sorted(fields)},
        "fields": fields,
        "requiresReview": any(item["provenance"]["requiresReview"] for item in fields.values()),
    }


def load_json_candidate(path: str | os.PathLike[str]) -> dict[str, Any]:
    source = Path(path)
    if source.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("candidate exceeds the byte limit")
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("candidate is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("candidate must be a JSON object")
    return value
