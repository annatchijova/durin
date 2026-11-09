"""Cross-source field contradiction detection for AI-extracted invoice drafts.

`supplier_operations.analyze_supplier_batch` already flags
`CONFLICTING_INVOICE_FACTS` when the same (supplier, invoiceNumber) obligation
shows more than one (amount, currency) pair, and already flags policy
violations (`RECIPIENT_NOT_APPROVED`, `CURRENCY_NOT_SUPPORTED`,
`EXCEEDS_PER_PAYMENT_LIMIT`) per row. This module does not repeat either of
those; it covers the fields the deterministic engine does not compare across
sources at all: `recipient`, `dueDate`, and `concept`. A different PayPal
recipient cited by two documents for the same obligation is a real signal
(typo or redirect) that would otherwise only surface if the amount also
happened to differ.

This module decides nothing about which value is correct. It only names a
disagreement and keeps both sides with their provenance, so a human reviewer
sees the conflict instead of a silently picked value. It runs on invoices
that already passed `source_ingestion.validate_invoice_extraction`, so every
value here is already grounded in a cited source excerpt.
"""

from __future__ import annotations

from typing import Any


COMPARED_FIELDS = ("recipient", "dueDate", "concept")
MAX_INVOICES = 500


def detect_source_contradictions(invoices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag cross-source mismatches in fields the engine does not already compare.

    `invoices` must be the enriched rows produced by
    `source_workflow.build_report_from_extractions` before they reach the
    supplier report: each has `supplier`, `invoiceNumber`, and a `provenance`
    map of field -> {value, provenance: {sourceId, sourceHash, evidenceExcerpt, ...}}.
    """
    if not isinstance(invoices, list) or len(invoices) > MAX_INVOICES:
        raise ValueError("invoices must be a bounded array")
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for invoice in invoices:
        if not isinstance(invoice, dict):
            raise ValueError("invoices must contain objects")
        groups.setdefault(_obligation_key(invoice), []).append(invoice)
    findings: list[dict[str, Any]] = []
    for (supplier, number), group in groups.items():
        source_ids = {_provenance_for(item, "supplier").get("sourceId") or item.get("invoiceId") for item in group}
        if len(group) < 2 or len(source_ids) < 2:
            continue
        for field in COMPARED_FIELDS:
            observed: dict[str, dict[str, Any]] = {}
            for item in group:
                value = str(item.get(field, "")).strip()
                if not value:
                    continue
                provenance = _provenance_for(item, field)
                observed.setdefault(value.casefold(), {"value": value, "sources": []})
                observed[value.casefold()]["sources"].append({
                    "invoiceId": item.get("invoiceId"),
                    "sourceId": provenance.get("sourceId"),
                    "sourceHash": provenance.get("sourceHash"),
                    "evidenceExcerpt": provenance.get("evidenceExcerpt"),
                })
            if len(observed) > 1:
                findings.append({
                    "type": "CROSS_SOURCE_FIELD_MISMATCH",
                    "supplier": supplier,
                    "invoiceNumber": number,
                    "field": field,
                    "observedValues": list(observed.values()),
                    "requiresReview": True,
                })
    return findings


def _obligation_key(invoice: dict[str, Any]) -> tuple[str, str]:
    supplier = str(invoice.get("supplier", "")).strip().casefold()
    number = str(invoice.get("invoiceNumber", "")).strip().casefold()
    if not supplier or not number:
        raise ValueError("invoice is missing supplier or invoiceNumber")
    return supplier, number


def _provenance_for(invoice: dict[str, Any], field: str) -> dict[str, Any]:
    provenance = invoice.get("provenance")
    if not isinstance(provenance, dict):
        return {}
    entry = provenance.get(field)
    return entry.get("provenance", {}) if isinstance(entry, dict) else {}
