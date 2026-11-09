"""Durable draft/review state for AI-produced extraction candidates.

An extraction candidate from `openai_extractor.py` is a draft, not a fact. This
ledger records it as DRAFT, lets a merchant move it to REVIEWED or REJECTED,
and keeps the full history. It never promotes a draft to accepted on its own;
`source_workflow.build_report_from_extractions` still re-validates every field
against the source before any draft reaches the supplier report.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


MAX_CANDIDATE_BYTES = 200_000


class DraftLedger:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @classmethod
    def from_env(cls) -> "DraftLedger | None":
        path = os.environ.get("DURIN_DRAFT_LEDGER_PATH", "").strip()
        return cls(path) if path else None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS extraction_drafts (
                    source_id TEXT PRIMARY KEY,
                    source_hash TEXT NOT NULL,
                    extractor_version TEXT NOT NULL,
                    candidate_json TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('DRAFT', 'REVIEWED', 'REJECTED')),
                    review_note TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def record_draft(self, *, source_id: str, source_hash: str, extractor_version: str, candidate: dict[str, Any], now: str) -> None:
        raw_candidate = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(raw_candidate.encode("utf-8")) > MAX_CANDIDATE_BYTES:
            raise ValueError("candidate exceeds the draft ledger size limit")
        source_id = _required(source_id, "source_id")
        source_hash = _required(source_hash, "source_hash")
        extractor_version = _required(extractor_version, "extractor_version")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT state FROM extraction_drafts WHERE source_id = ?", (source_id,)).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO extraction_drafts (source_id, source_hash, extractor_version, candidate_json, state, created_at, updated_at) VALUES (?, ?, ?, ?, 'DRAFT', ?, ?)",
                    (source_id, source_hash, extractor_version, raw_candidate, now, now),
                )
            elif row[0] == "DRAFT":
                connection.execute(
                    "UPDATE extraction_drafts SET source_hash = ?, extractor_version = ?, candidate_json = ?, updated_at = ? WHERE source_id = ? AND state = 'DRAFT'",
                    (source_hash, extractor_version, raw_candidate, now, source_id),
                )
            else:
                connection.rollback()
                raise ValueError(f"draft for {source_id} is already {row[0]}; it is not re-extracted silently")
            connection.commit()

    def set_review_state(self, *, source_id: str, state: str, review_note: str | None, now: str) -> None:
        if state not in ("REVIEWED", "REJECTED"):
            raise ValueError("state must be REVIEWED or REJECTED")
        source_id = _required(source_id, "source_id")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT state FROM extraction_drafts WHERE source_id = ?", (source_id,)).fetchone()
            if row is None:
                connection.rollback()
                raise ValueError("draft is not recorded")
            if row[0] != "DRAFT":
                connection.rollback()
                raise ValueError(f"draft for {source_id} is already {row[0]}")
            connection.execute(
                "UPDATE extraction_drafts SET state = ?, review_note = ?, updated_at = ? WHERE source_id = ? AND state = 'DRAFT'",
                (state, review_note, now, source_id),
            )
            connection.commit()

    def get(self, source_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT source_id, source_hash, extractor_version, candidate_json, state, review_note, created_at, updated_at FROM extraction_drafts WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return _row_to_dict(row) if row else None

    def list_drafts(self, *, state: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT source_id, source_hash, extractor_version, candidate_json, state, review_note, created_at, updated_at FROM extraction_drafts"
        params: tuple[Any, ...] = ()
        if state is not None:
            query += " WHERE state = ?"
            params = (state,)
        query += " ORDER BY source_id"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    source_id, source_hash, extractor_version, candidate_json, state, review_note, created_at, updated_at = row
    return {
        "sourceId": source_id,
        "sourceHash": source_hash,
        "extractorVersion": extractor_version,
        "candidate": json.loads(candidate_json),
        "state": state,
        "reviewNote": review_note,
        "createdAt": created_at,
        "updatedAt": updated_at,
    }


def _required(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return value.strip()
