"""Deterministic transaction-history search: date chunking, normalization,
and filtering. No network access, no model call -- this is the boundary
that keeps a natural-language question from ever directly producing a
transaction record. The caller supplies hints (possibly from a model); this
module decides which real, already-fetched PayPal records match them.
"""

from __future__ import annotations

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


def filter_transactions(
    transactions: list[dict[str, Any]],
    *,
    counterparty_hint: str | None = None,
    amount_hint: str | None = None,
    keywords: list[str] | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Deterministically rank already-fetched, real transactions against hints.

    A hint that matches nothing is not an error: it just narrows to zero
    results, which the caller must report as "not found," never as a
    fabricated best guess.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or not (1 <= limit <= 100):
        raise ValueError("limit must be between 1 and 100")
    matched = []
    for transaction in transactions:
        if amount_hint and not _matches_amount(transaction, amount_hint):
            continue
        if counterparty_hint and not _matches_text(
            [transaction["counterpartyEmail"], transaction["counterpartyName"]], counterparty_hint
        ):
            continue
        if keywords:
            haystacks = [transaction["subject"], transaction["note"], transaction["invoiceId"], transaction["transactionId"]]
            if not any(_matches_text(haystacks, keyword) for keyword in keywords):
                continue
        matched.append(transaction)
    matched.sort(key=lambda t: t["date"], reverse=True)
    return matched[:limit]
