"""Immutable proposal and explicit human-approval boundary."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def proposal_digest(proposal: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(proposal)).hexdigest()


def create_immutable_proposal(
    *,
    accepted: list[dict[str, Any]],
    currency: str,
    total_amount: str,
    policy_version: str,
    evidence_refs: list[str],
    proposal_id: str,
    created_at: str,
    expires_at: str,
) -> dict[str, Any]:
    """Create a review-only proposal whose meaningful fields are digest-bound."""
    if not accepted:
        raise ValueError("proposal must contain at least one accepted item")
    if not policy_version or not proposal_id or not created_at or not expires_at:
        raise ValueError("proposal identity, policy version, and timestamps are required")
    _valid_interval(created_at, expires_at)
    if not isinstance(evidence_refs, list) or any(not isinstance(item, str) or not item for item in evidence_refs):
        raise ValueError("evidence_refs must be a list of non-empty strings")
    items = sorted(accepted, key=lambda item: str(item.get("invoiceId", "")))
    proposal = {
        "schemaVersion": 1,
        "proposalId": proposal_id,
        "flow": "PAYABLE",
        "items": items,
        "currency": currency,
        "totalAmount": total_amount,
        "policyVersion": policy_version,
        "evidenceRefs": sorted(set(evidence_refs)),
        "createdAt": created_at,
        "expiresAt": expires_at,
        "status": "PENDING_APPROVAL",
        "execution": "NO_PAYMENT_SUBMITTED",
    }
    return {"proposal": proposal, "proposalDigest": proposal_digest(proposal)}


def approve_proposal(
    *, proposal: dict[str, Any], expected_digest: str, approver_id: str, approved_at: str
) -> dict[str, Any]:
    """Approve exactly the digest presented to a human; never execute it."""
    if proposal_digest(proposal) != expected_digest:
        raise ValueError("proposal digest does not match the presented proposal")
    if proposal.get("status") != "PENDING_APPROVAL":
        raise ValueError("proposal is not pending approval")
    _valid_interval(proposal["createdAt"], approved_at)
    _valid_interval(approved_at, proposal["expiresAt"])
    if not approver_id:
        raise ValueError("approver_id is required")
    return {
        "authorizationId": hashlib.sha256(f"{expected_digest}:{approver_id}:{approved_at}".encode()).hexdigest()[:24],
        "proposalDigest": expected_digest,
        "approverId": approver_id,
        "approvedAt": approved_at,
        "expiresAt": proposal["expiresAt"],
        "status": "APPROVED",
        "execution": "NOT_EXECUTED",
    }


def _valid_interval(start: str, end: str) -> None:
    try:
        if datetime.fromisoformat(start.replace("Z", "+00:00")) > datetime.fromisoformat(end.replace("Z", "+00:00")):
            raise ValueError("timestamps are out of order")
    except ValueError as exc:
        raise ValueError("timestamps must be ordered ISO timestamps") from exc
