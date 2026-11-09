"""Fail-closed OpenAI client for the transaction-search chat assistant.

Two roles, deliberately kept apart so the model never gets near a value it
could alter:

- `interpret_query` reads a free-text question and proposes search hints
  (how far back to look, who, how much, which keywords). This is a guess,
  never ground truth -- paypal_transaction_search.py decides what actually
  matches, against real data already fetched from PayPal.
- `narrate_results` reads the real, already-filtered transactions and turns
  them into prose. It is instructed to use only the given data and is never
  shown anything it could use to invent a transaction that was not returned.

Mirrors the fail-closed shape of paypal_client.py / openai_extractor.py.
"""

from __future__ import annotations

import json
from typing import Any

from openai_extractor import OpenAIExtractionClient, OpenAIProviderError


MAX_QUESTION_CHARS = 2000
MAX_TRANSACTIONS_FOR_NARRATION = 15

_INTERPRET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "monthsBack": {"type": "integer", "minimum": 1, "maximum": 24},
        "counterpartyHint": {"type": ["string", "null"], "maxLength": 200},
        "amountHint": {"type": ["string", "null"], "maxLength": 32},
        "keywords": {"type": "array", "items": {"type": "string", "maxLength": 100}, "maxItems": 5},
    },
    "required": ["monthsBack", "counterpartyHint", "amountHint", "keywords"],
}

_INTERPRET_SYSTEM_PROMPT = (
    "You read a merchant's question about a past PayPal payment and propose "
    "search parameters. You never answer the question yourself and never "
    "claim a transaction exists. monthsBack: how far back to search, your "
    "best guess from the question (default 6 if unstated, max 24). "
    "counterpartyHint: a name or email substring to look for, or null. "
    "amountHint: a bare decimal number if an amount was mentioned, or null -- "
    "never include a currency symbol or code. keywords: up to 5 short terms "
    "from the question useful for matching an invoice subject or note."
)

_NARRATE_SYSTEM_PROMPT = (
    "You are explaining real PayPal transaction search results to a "
    "merchant. You will be given the merchant's question and a JSON array "
    "of transactions that a deterministic search already matched -- this "
    "array is the complete and only truth available to you. Answer using "
    "only what is in the array: cite transaction id, date, amount, currency, "
    "and counterparty for anything you reference. If the array is empty, "
    "say plainly that nothing matching was found in the searched period -- "
    "never invent a transaction, never guess at one that might exist outside "
    "the array. Keep the answer to a few sentences."
)


class OpenAIChatClient:
    def __init__(self, extraction_client: OpenAIExtractionClient):
        self._client = extraction_client

    def interpret_query(self, question: str) -> dict[str, Any]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question is required")
        if len(question) > MAX_QUESTION_CHARS:
            raise ValueError(f"question exceeds {MAX_QUESTION_CHARS} characters")
        payload = {
            "model": self._client.config.model,
            "messages": [
                {"role": "system", "content": _INTERPRET_SYSTEM_PROMPT},
                {"role": "user", "content": question.strip()},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "search_hints", "strict": True, "schema": _INTERPRET_SCHEMA},
            },
            "temperature": 0,
            "max_tokens": 300,
        }
        response = self._client.chat_completion(payload)
        return self._parse_json_message(response)

    def narrate_results(self, *, question: str, transactions: list[dict[str, Any]]) -> str:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question is required")
        bounded = transactions[:MAX_TRANSACTIONS_FOR_NARRATION]
        payload = {
            "model": self._client.config.model,
            "messages": [
                {"role": "system", "content": _NARRATE_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"question": question.strip(), "transactions": bounded}, ensure_ascii=False)},
            ],
            "temperature": 0,
            "max_tokens": 500,
        }
        response = self._client.chat_completion(payload)
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenAIProviderError(None, "OpenAI response had no choices", response)
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content:
            raise OpenAIProviderError(None, "OpenAI response had no message content", response)
        return content

    def _parse_json_message(self, response: dict[str, Any]) -> dict[str, Any]:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenAIProviderError(None, "OpenAI response had no choices", response)
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content:
            raise OpenAIProviderError(None, "OpenAI response had no message content", response)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OpenAIProviderError(None, "OpenAI content was not valid JSON", content) from exc
        if not isinstance(parsed, dict):
            raise OpenAIProviderError(None, "OpenAI hints must be an object", parsed)
        return parsed
