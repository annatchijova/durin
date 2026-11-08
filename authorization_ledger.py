"""Durable authorization and submission state for PayPal execution.

The ledger is the local transactional authority. It does not make the remote
PayPal call atomic; it records the intermediate state so retries and recovery
are explicit and idempotent.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


MAX_RESPONSE_BYTES = 2_000_000


def payload_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class AuthorizationLedger:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @classmethod
    def from_env(cls) -> "AuthorizationLedger | None":
        path = os.environ.get("DURIN_AUTHORIZATION_LEDGER_PATH", "").strip()
        return cls(path) if path else None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS authorization_ledger (
                    authorization_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL,
                    proposal_digest TEXT NOT NULL UNIQUE,
                    payload_fingerprint TEXT,
                    state TEXT NOT NULL CHECK (state IN ('APPROVED', 'IN_FLIGHT', 'SUBMITTED')),
                    provider_response TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def record_approval(self, authorization: dict[str, Any]) -> None:
        authorization_id = _required(authorization, "authorizationId")
        proposal_id = _required(authorization, "proposalId")
        proposal_digest = _required(authorization, "proposalDigest")
        now = _required(authorization, "approvedAt")
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO authorization_ledger (authorization_id, proposal_id, proposal_digest, state, created_at, updated_at) VALUES (?, ?, ?, 'APPROVED', ?, ?)",
                    (authorization_id, proposal_id, proposal_digest, now, now),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise ValueError("proposal or authorization has already been recorded") from exc

    def reserve_submission(self, authorization_id: str, payload: dict[str, Any], now: str) -> None:
        fingerprint = payload_fingerprint(payload)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state, payload_fingerprint FROM authorization_ledger WHERE authorization_id = ?",
                (authorization_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise ValueError("authorization is not recorded")
            state, previous_fingerprint = row
            if previous_fingerprint and previous_fingerprint != fingerprint:
                connection.rollback()
                raise ValueError("idempotency key was reused for a different payload")
            if state == "SUBMITTED":
                connection.rollback()
                raise ValueError("authorization has already been submitted")
            if state == "IN_FLIGHT":
                connection.rollback()
                raise ValueError("authorization is in flight; recover by sender_batch_id")
            connection.execute(
                "UPDATE authorization_ledger SET state = 'IN_FLIGHT', payload_fingerprint = ?, updated_at = ? WHERE authorization_id = ? AND state = 'APPROVED'",
                (fingerprint, now, authorization_id),
            )
            connection.commit()

    def mark_submitted(self, authorization_id: str, payload: dict[str, Any], response: dict[str, Any], now: str) -> None:
        raw_response = json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(raw_response.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise ValueError("provider response exceeds ledger size limit")
        fingerprint = payload_fingerprint(payload)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state, payload_fingerprint FROM authorization_ledger WHERE authorization_id = ?",
                (authorization_id,),
            ).fetchone()
            if row is None or row[1] != fingerprint:
                connection.rollback()
                raise ValueError("authorization payload does not match ledger")
            if row[0] == "SUBMITTED":
                connection.rollback()
                raise ValueError("authorization has already been submitted")
            if row[0] != "IN_FLIGHT":
                connection.rollback()
                raise ValueError("authorization is not in flight")
            connection.execute(
                "UPDATE authorization_ledger SET state = 'SUBMITTED', provider_response = ?, updated_at = ? WHERE authorization_id = ? AND state = 'IN_FLIGHT'",
                (raw_response, now, authorization_id),
            )
            connection.commit()


def _required(value: dict[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"{field} is required")
    return result.strip()
