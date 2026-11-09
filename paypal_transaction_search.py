"""Deterministic transaction-history search: date chunking, normalization,
and filtering. No network access, no model call -- this is the boundary
that keeps a natural-language question from ever directly producing a
transaction record. The caller supplies hints (possibly from a model); this
module decides which real, already-fetched PayPal records match them.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


MAX_RANGE_DAYS = 31  # PayPal's own per-request window limit for Transaction Search.
MAX_CHUNKS = 24  # bounds a single search to ~2 years of monthly chunks.
MAX_MONTHS_BACK = 24


def _paypal_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S-0000")


def chunk_date_range(*, months_back: int, now: datetime | None = None) -> list[tuple[str, str]]:
    """Split "the last N months" into PayPal-API-sized (<=31 day) windows.

    Returns oldest-to-newest (start, end) ISO-ish timestamp pairs, each
    ready to pass straight to PayPalSandboxClient.search_transactions.
    """
    if isinstance(months_back, bool) or not isinstance(months_back, int) or not (1 <= months_back <= MAX_MONTHS_BACK):
        raise ValueError(f"months_back must be between 1 and {MAX_MONTHS_BACK}")
    end = now or datetime.now(timezone.utc)
    start = end - timedelta(days=months_back * 31)
    chunks: list[tuple[str, str]] = []
    cursor = start
    while cursor < end and len(chunks) < MAX_CHUNKS:
        chunk_end = min(cursor + timedelta(days=MAX_RANGE_DAYS), end)
        chunks.append((_paypal_timestamp(cursor), _paypal_timestamp(chunk_end)))
        cursor = chunk_end
    return chunks


def normalize_transaction(raw: dict[str, Any]) -> dict[str, Any]:
    """Pull the fields this product cares about out of one raw PayPal record.

    Tolerant of missing nested keys -- PayPal's Transaction Search response
    shape varies by transaction type (payout item vs. regular payment), and
    a missing field here must become an empty string, never a crash that
    drops every other transaction in the page.
    """
    info = raw.get("transaction_info") if isinstance(raw.get("transaction_info"), dict) else {}
    payer = raw.get("payer_info") if isinstance(raw.get("payer_info"), dict) else {}
    amount = info.get("transaction_amount") if isinstance(info.get("transaction_amount"), dict) else {}
    payer_name = payer.get("payer_name") if isinstance(payer.get("payer_name"), dict) else {}
    return {
        "transactionId": str(info.get("transaction_id", "")),
        "date": str(info.get("transaction_initiation_date", "")),
        "updatedDate": str(info.get("transaction_updated_date", "")),
        "amountValue": str(amount.get("value", "")),
        "currency": str(amount.get("currency_code", "")),
        "status": str(info.get("transaction_status", "")),
        "eventCode": str(info.get("transaction_event_code", "")),
        "subject": str(info.get("transaction_subject", "")),
        "note": str(info.get("transaction_note", "")),
        "invoiceId": str(info.get("invoice_id", "")),
        "counterpartyEmail": str(payer.get("email_address", "")),
        "counterpartyName": str(payer_name.get("alternate_full_name", "")),
    }


def _matches_amount(transaction: dict[str, Any], amount_hint: str) -> bool:
    try:
        target = abs(Decimal(amount_hint))
        value = abs(Decimal(transaction["amountValue"])) if transaction["amountValue"] else None
    except InvalidOperation:
        return False
    if value is None:
        return False
    tolerance = max(target * Decimal("0.02"), Decimal("0.01"))
    return abs(value - target) <= tolerance


def _matches_text(haystacks: list[str], needle: str) -> bool:
    needle_cf = needle.strip().casefold()
    return bool(needle_cf) and any(needle_cf in haystack.casefold() for haystack in haystacks if haystack)


def _matches_keyword(haystacks: list[str], keyword: str) -> bool:
    """Whole-word match only.

    A generic keyword like "pay" from an everyday question ("did we *pay*
    ... recently") is a plain substring of "Durin approved supplier
    *pay*out" -- the subject on every single payout this product creates.
    Substring matching here would mark nearly every transaction as
    "matching the question," burying the one the amount hint already
    correctly ranked first. Word-boundary matching keeps that false
    positive out without needing a hand-maintained stopword list.
    """
    word = keyword.strip()
    if len(word) < 3:
        return False
    pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    return any(pattern.search(haystack) for haystack in haystacks if haystack)


def filter_transactions(
    transactions: list[dict[str, Any]],
    *,
    counterparty_hint: str | None = None,
    amount_hint: str | None = None,
    keywords: list[str] | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Deterministically rank already-fetched, real transactions against hints.

    Hints are scored, not required all-at-once: PayPal's own record only
    knows a counterparty's email, never a business name Durin itself
    extracted from an invoice, so a natural-language question's name hint
    routinely cannot match anything in PayPal's data even when the amount
    hint is exactly right. Requiring every hint to match would silently
    throw away a real transaction because of a hint that was never
    checkable against PayPal's fields; scoring keeps it ranked below a
    transaction that matches on every hint, rather than discarding it.

    When no hint is given at all, every transaction scores zero and all are
    returned (most recent first). When hints are given but none matches
    anything, the result is empty -- that is a real "not found," never a
    fabricated best guess.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or not (1 <= limit <= 100):
        raise ValueError("limit must be between 1 and 100")
    hints_given = bool(amount_hint) or bool(counterparty_hint) or bool(keywords)
    scored: list[tuple[int, dict[str, Any]]] = []
    for transaction in transactions:
        score = 0
        if amount_hint and _matches_amount(transaction, amount_hint):
            score += 1
        if counterparty_hint and _matches_text(
            [transaction["counterpartyEmail"], transaction["counterpartyName"]], counterparty_hint
        ):
            score += 1
        if keywords:
            haystacks = [transaction["subject"], transaction["note"], transaction["invoiceId"], transaction["transactionId"]]
            if any(_matches_keyword(haystacks, keyword) for keyword in keywords):
                score += 1
        if not hints_given or score > 0:
            scored.append((score, transaction))
    scored.sort(key=lambda item: (item[0], item[1]["date"]), reverse=True)
    return [transaction for _, transaction in scored[:limit]]
