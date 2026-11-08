# Durable Authorization Ledger Audit — 2026-11-08

## Objective

Close the previously documented multi-process replay gap without holding a
mutex across the PayPal network call and without claiming atomicity across the
local database and PayPal.

Skills applied: `distributed-write-atomicity`, `atomic-state-mutation`,
`concurrency-reasoning`, `audit-before-patch`, `falsifiable-testing`,
`honest-degradation`, and `recovery-integrity`.

## Implementation reviewed

`authorization_ledger.py` is a SQLite transactional authority with:

- unique `authorization_id` and `proposal_digest` constraints;
- `WAL` journal mode and a five-second busy timeout;
- `BEGIN IMMEDIATE` for state transitions;
- payload fingerprinting to reject idempotency-key reuse with a different body;
- explicit states:

```text
APPROVED -> IN_FLIGHT -> SUBMITTED
```

The PayPal HTTP call is not inside the SQLite transaction. The ledger reserves
the authorization before the call, and records `SUBMITTED` only after a
successful provider response. An exception or timeout leaves `IN_FLIGHT`, so
recovery must query PayPal with the same `sender_batch_id` before deciding what
to do.

## Tests executed

- `python3 -m unittest discover -s . -p 'test_*.py'`: **62 passed, 0 failed,
  0 skipped**.
- Durable ledger unit tests: unique approval, state transitions, payload
  fingerprint mismatch, and submitted replay.
- Client integration test: a successful fake provider response transitions the
  ledger and a second attempt is rejected before another provider request.
- Existing red-team probes and variant probes: executed offline.
- `python3 -m compileall -q .`: passed.
- `git diff --check`: passed.

## Findings closed

| Finding | Result |
| --- | --- |
| Replay between processes when a shared ledger is configured | Closed by SQLite uniqueness and transactional state transitions. |
| Check-then-send race across workers | Closed at reservation time by `BEGIN IMMEDIATE`; no application-only lookup decides the winner. |
| Same idempotency key with a different body | Rejected by payload fingerprint comparison. |
| Authorization approval duplicated for the same proposal | Rejected by unique `proposal_digest` when the ledger is configured. |
| Authorization consumed before network execution | Corrected; consumption is recorded only after a successful provider response. |
| Local mutex held across network I/O | Durable path no longer uses the process mutex across I/O. |

## Residual boundaries

### R-LEDGER-01 — Ledger configuration is mandatory for multi-process guarantees

**Status:** Confirmed design boundary

The durable guarantee exists only when all workers use the same
`DURIN_AUTHORIZATION_LEDGER_PATH` and stable `DURIN_AUTHORIZATION_KEY`. If the
variable is absent, the compatibility fallback is process-local and must not be
used as a production multi-worker control.

### R-LEDGER-02 — Local database and PayPal remain separate authorities

**Status:** Expected distributed-systems limitation

If PayPal accepts the request and the process dies before `SUBMITTED` commits,
the row remains `IN_FLIGHT`. This is intentional honest degradation. The
recovery operation is a PayPal lookup by the same `sender_batch_id`; the system
does not claim exactly-once delivery across the external provider.

### R-LEDGER-03 — Shared SQLite storage must itself be suitable for deployment

**Status:** Operational prerequisite

All workers must reach the same durable SQLite file with correct filesystem
locking semantics. A per-container filesystem, copied file, or non-shared
volume defeats the cross-process guarantee. A managed database may be preferable
for production scale, but it is outside this preparation scope.

## Decision

**The durable local authorization boundary is ready for controlled Sandbox
integration when the shared ledger path and stable secrets are configured.**
The system still makes no claim that a PayPal network call and a local commit
are one atomic transaction, and no real transaction was sent during this audit.
