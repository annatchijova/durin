"""Fail-closed PayPal Sandbox HTTP client.

The MCP never imports this module. It is an application-side adapter for the
future explicit merchant-approved execution path.
"""

from __future__ import annotations

import base64
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable


MAX_RESPONSE_BYTES = 2_000_000
DEFAULT_BASE_URL = "https://api-m.sandbox.paypal.com"
_PAYOUT_SUBMISSION_LOCK = Lock()


class PayPalProviderError(RuntimeError):
    def __init__(self, status: int | None, message: str, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass(frozen=True)
class PayPalSandboxConfig:
    client_id: str
    client_secret: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 15.0

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "PayPalSandboxConfig":
        values = os.environ if environ is None else environ
        config = cls(
            client_id=values.get("PAYPAL_CLIENT_ID", ""),
            client_secret=values.get("PAYPAL_CLIENT_SECRET", ""),
            base_url=values.get("PAYPAL_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not self.client_id or not self.client_secret:
            raise ValueError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET are required")
        if not self.base_url.startswith(("https://", "http://")):
            raise ValueError("PAYPAL_BASE_URL must be an HTTP(S) URL")
        parsed = urllib.parse.urlsplit(self.base_url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise ValueError("PAYPAL_BASE_URL cannot contain credentials, query, or fragment")
        hostname = (parsed.hostname or "").lower()
        if hostname != "api-m.sandbox.paypal.com" and hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("only PayPal Sandbox or loopback endpoints are permitted")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)) or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0 or self.timeout_seconds > 60:
            raise ValueError("timeout_seconds must be between 0 and 60")


class PayPalSandboxClient:
    def __init__(self, config: PayPalSandboxConfig, opener: Callable[..., Any] | None = None):
        config.validate()
        self.config = config
        self._opener = opener or urllib.request.urlopen

    def create_payout(self, payload: dict[str, Any], sender_batch_id: str) -> dict[str, Any]:
        if not sender_batch_id or len(sender_batch_id) > 256:
            raise ValueError("sender_batch_id is required and bounded")
        payload_batch_id = payload.get("sender_batch_header", {}).get("sender_batch_id") if isinstance(payload, dict) else None
        if payload_batch_id != sender_batch_id:
            raise ValueError("sender_batch_id must match payload sender_batch_id")
        authorization_id = payload.get("durin", {}).get("authorizationId") if isinstance(payload.get("durin"), dict) else None
        from authorization_ledger import AuthorizationLedger
        ledger = AuthorizationLedger.from_env()
        if authorization_id and ledger is None:
            raise ValueError("durable authorization ledger is required for authorized payout")
        if authorization_id and ledger is not None:
            ledger.reserve_submission(authorization_id, payload, datetime.now(timezone.utc).isoformat())
            return self._submit_payout(payload, sender_batch_id, authorization_id, ledger)
        with _PAYOUT_SUBMISSION_LOCK:
            result = self._submit_payout(payload, sender_batch_id, authorization_id, None)
            return result

    def _submit_payout(self, payload: dict[str, Any], sender_batch_id: str, authorization_id: str | None, ledger: Any) -> dict[str, Any]:
        result = self._json_request(
            "/v1/payments/payouts",
            method="POST",
            body=payload,
            headers={"PayPal-Request-Id": sender_batch_id},
        )
        if authorization_id and ledger is not None:
            ledger.mark_submitted(authorization_id, payload, result, datetime.now(timezone.utc).isoformat())
        elif authorization_id:
            from paypal_payouts import mark_authorization_submitted
            mark_authorization_submitted(authorization_id)
        return result

    def get_payout(self, payout_batch_id: str) -> dict[str, Any]:
        if not payout_batch_id or len(payout_batch_id) > 30:
            raise ValueError("payout_batch_id is required and bounded")
        return self._json_request(f"/v1/payments/payouts/{urllib.parse.quote(payout_batch_id, safe='')}", method="GET")

    def finalize_payout_recovery(self, payload: dict[str, Any], provider_response: dict[str, Any], provider_batch_id: str) -> None:
        """Finalize an IN_FLIGHT ledger row after a provider batch lookup."""
        authorization_id = payload.get("durin", {}).get("authorizationId") if isinstance(payload.get("durin"), dict) else None
        if not authorization_id:
            raise ValueError("payload authorization identity is required")
        from authorization_ledger import AuthorizationLedger
        ledger = AuthorizationLedger.from_env()
        if ledger is None:
            raise ValueError("durable authorization ledger is required for recovery")
        ledger.recover_submission(authorization_id, payload, provider_response, provider_batch_id, datetime.now(timezone.utc).isoformat())

    def _access_token(self) -> str:
        raw = f"{self.config.client_id}:{self.config.client_secret}".encode()
        response = self._request(
            "/v1/oauth2/token",
            method="POST",
            body=b"grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {base64.b64encode(raw).decode()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        token = response.get("access_token")
        if not isinstance(token, str) or not token:
            raise PayPalProviderError(None, "PayPal token response did not contain access_token", response)
        return token

    def _json_request(self, path: str, *, method: str, body: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        token = self._access_token()
        return self._request(
            path,
            method=method,
            body=json.dumps(body, separators=(",", ":")).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", **(headers or {})},
        )

    def _request(self, path: str, *, method: str, body: bytes | None, headers: dict[str, str]) -> dict[str, Any]:
        request = urllib.request.Request(f"{self.config.base_url}{path}", data=body, headers=headers, method=method)
        try:
            with self._opener(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise PayPalProviderError(getattr(response, "status", None), "PayPal response exceeds size limit")
                parsed = json.loads(raw.decode("utf-8"))
                if not isinstance(parsed, dict):
                    raise PayPalProviderError(getattr(response, "status", None), "PayPal response must be an object", parsed)
                if getattr(response, "status", 200) >= 400:
                    raise PayPalProviderError(response.status, "PayPal request failed", parsed)
                return parsed
        except PayPalProviderError:
            raise
        except urllib.error.HTTPError as exc:
            raw = exc.read(MAX_RESPONSE_BYTES)
            try:
                body_json = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                body_json = None
            raise PayPalProviderError(exc.code, "PayPal request failed", body_json) from exc
        except (OSError, urllib.error.URLError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PayPalProviderError(None, f"PayPal transport or JSON failure: {exc}") from exc
