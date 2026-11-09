"""Fail-closed OpenAI structured-extraction client.

This module never decides anything. It turns one authorized source's text
into a draft candidate shaped for `source_ingestion.validate_invoice_extraction`.
The draft is untrusted until that validation grounds every field in an
evidence excerpt taken from the source content; a hallucinated value with no
matching excerpt is rejected there, not here.

The MCP never imports this module. It is an application-side pipeline step,
mirroring the fail-closed shape of `paypal_client.py`.
"""

from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from source_ingestion import ALLOWED_INVOICE_FIELDS


MAX_RESPONSE_BYTES = 2_000_000
DEFAULT_BASE_URL = "https://api.openai.com"
DEFAULT_MODEL = "gpt-4o-mini"

_MAX_FIELD_LENGTH = 256
_MAX_EVIDENCE_LENGTH = 1000

_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **{field: {"type": "string", "maxLength": _MAX_FIELD_LENGTH} for field in ALLOWED_INVOICE_FIELDS},
        "evidence": {
            "type": "object",
            "additionalProperties": False,
            "properties": {field: {"type": "string", "maxLength": _MAX_EVIDENCE_LENGTH} for field in ALLOWED_INVOICE_FIELDS},
            "required": sorted(ALLOWED_INVOICE_FIELDS),
        },
    },
    "required": sorted(ALLOWED_INVOICE_FIELDS) + ["evidence"],
}

_SYSTEM_PROMPT = (
    "You extract invoice fields from one document's text. You never decide "
    "anything financial; you only transcribe what the text literally states. "
    "The 'amount' field must be ONLY digits and at most one decimal point "
    "(e.g. '500.00'), with no currency code, symbol, thousands separator, or "
    "any other character; put the currency code in the separate 'currency' "
    "field instead. The 'currency' field must be exactly a three-letter ISO "
    "code (e.g. 'USD'). For every field, copy a short verbatim excerpt from "
    "the given text into evidence[field] that contains the value. If a field "
    "is not present in the text, you must still return your best literal "
    "reading, but the excerpt you cite will be checked against the source "
    "text and rejected if it is not an exact substring."
)


class OpenAIProviderError(RuntimeError):
    def __init__(self, status: int | None, message: str, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass(frozen=True)
class OpenAIExtractionConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "OpenAIExtractionConfig":
        values = os.environ if environ is None else environ
        config = cls(
            api_key=values.get("OPENAI_API_KEY", ""),
            base_url=values.get("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            model=values.get("OPENAI_EXTRACTION_MODEL", DEFAULT_MODEL),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        if not self.base_url.startswith("https://"):
            raise ValueError("OPENAI_BASE_URL must be an HTTPS URL")
        if not self.model or len(self.model) > 128:
            raise ValueError("OPENAI_EXTRACTION_MODEL is invalid")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)) or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0 or self.timeout_seconds > 120:
            raise ValueError("timeout_seconds must be between 0 and 120")


class OpenAIExtractionClient:
    """Produces a draft candidate; never writes it anywhere and never approves it."""

    def __init__(self, config: OpenAIExtractionConfig, opener: Callable[..., Any] | None = None):
        config.validate()
        self.config = config
        self._opener = opener or urllib.request.urlopen

    def extract_candidate(self, *, source_content: str, source_kind: str) -> dict[str, Any]:
        if not isinstance(source_content, str) or not source_content.strip():
            raise ValueError("source_content is required")
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Document kind: {source_kind}\n\nDocument text:\n{source_content}"},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "invoice_extraction", "strict": True, "schema": _EXTRACTION_SCHEMA},
            },
            "temperature": 0,
            "max_tokens": 2000,
        }
        response = self._request(
            "/v1/chat/completions",
            body=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"},
        )
        return self._parse_candidate(response)

    def _parse_candidate(self, response: dict[str, Any]) -> dict[str, Any]:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenAIProviderError(None, "OpenAI response had no choices", response)
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content:
            raise OpenAIProviderError(None, "OpenAI response had no message content", response)
        try:
            candidate = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OpenAIProviderError(None, "OpenAI content was not valid JSON", content) from exc
        if not isinstance(candidate, dict):
            raise OpenAIProviderError(None, "OpenAI candidate must be an object", candidate)
        return candidate

    def _request(self, path: str, *, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
        request = urllib.request.Request(f"{self.config.base_url}{path}", data=body, headers=headers, method="POST")
        try:
            with self._opener(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise OpenAIProviderError(getattr(response, "status", None), "OpenAI response exceeds size limit")
                parsed = json.loads(raw.decode("utf-8"))
                if not isinstance(parsed, dict):
                    raise OpenAIProviderError(getattr(response, "status", None), "OpenAI response must be an object", parsed)
                if getattr(response, "status", 200) >= 400:
                    raise OpenAIProviderError(response.status, "OpenAI request failed", parsed)
                return parsed
        except OpenAIProviderError:
            raise
        except urllib.error.HTTPError as exc:
            raw = exc.read(MAX_RESPONSE_BYTES)
            try:
                body_json = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                body_json = None
            raise OpenAIProviderError(exc.code, "OpenAI request failed", body_json) from exc
        except (OSError, urllib.error.URLError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenAIProviderError(None, f"OpenAI transport or JSON failure: {exc}") from exc
