#!/usr/bin/env python3
"""Validate PayPal Sandbox execution prerequisites without network access."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from authorization_ledger import AuthorizationLedger
from paypal_client import PayPalSandboxConfig


REQUIRED_STABLE_KEYS = (
    "DURIN_AUTHORIZATION_KEY",
    "DURIN_PROVIDER_EVIDENCE_KEY",
    "DURIN_SOURCE_ATTESTATION_KEY",
)


def main() -> int:
    result: dict[str, object] = {"networkAccess": False, "transactionsSent": False}
    missing = [name for name in ("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "DURIN_AUTHORIZATION_LEDGER_PATH", *REQUIRED_STABLE_KEYS) if not os.environ.get(name)]
    if missing:
        result.update({"ok": False, "missing": missing})
        print(json.dumps(result, sort_keys=True))
        return 2
    try:
        PayPalSandboxConfig.from_env()
        ledger = AuthorizationLedger.from_env()
        if ledger is None:
            raise ValueError("DURIN_AUTHORIZATION_LEDGER_PATH is required")
        result.update({"ok": True, "sandboxHost": "api-m.sandbox.paypal.com", "ledgerPath": str(ledger.path)})
    except (OSError, ValueError) as exc:
        result.update({"ok": False, "error": str(exc)})
        print(json.dumps(result, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
