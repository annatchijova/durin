"""Fail-closed PayPal Sandbox HTTP client.

The MCP never imports this module. It is an application-side adapter for the
future explicit merchant-approved execution path.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


MAX_RESPONSE_BYTES = 2_000_000
DEFAULT_BASE_URL = "https://api-m.sandbox.paypal.com"


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
        hostname = self.base_url.split("//", 1)[1].split("/", 1)[0].split(":", 1)[0].lower()
        if hostname != "api-m.sandbox.paypal.com" and hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("only PayPal Sandbox or loopback endpoints are permitted")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 60:
            raise ValueError("timeout_seconds must be between 0 and 60")


class PayPalSandboxClient:
    def __init__(self, config: PayPalSandboxConfig, opener: Callable[..., Any] | None = None):
        config.validate()
        self.config = config
        self._opener = opener or urllib.request.urlopen

    def create_payout(self, payload: dict[str, Any], sender_batch_id: str) -> dict[str, Any]:
        if not sender_batch_id or len(sender_batch_id) > 256:
            raise ValueError("sender_batch_id is required and bounded")
        return self._json_request(
            "/v1/payments/payouts",
            method="POST",
            body=payload,
            headers={"PayPal-Request-Id": sender_batch_id},
        )

    def get_payout(self, payout_batch_id: str) -> dict[str, Any]:
        if not payout_batch_id or len(payout_batch_id) > 30:
            raise ValueError("payout_batch_id is required and bounded")
        return self._json_request(f"/v1/payments/payouts/{urllib.parse.quote(payout_batch_id, safe='')}", method="GET")

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
