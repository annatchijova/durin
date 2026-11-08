# Security Audit — Durin
## Red Team Round 1

**Date:** 2026-11-08
**Method:** Abductive Engineering (A-D-I) with red-team auditing, offensive business logic, agent trust boundaries, deterministic core, secret lifecycle, audit-before-patch, and falsifiable testing.
**Scope:** Python backend, MCP, source provenance, authorization, PayPal Payouts builder/client/reconciliation. Frontend, deployment, real credentials, and live payouts were out of scope.
**Base:** `main @ fbf11df`
**Probe:** `python3 scripts/redteam_round1.py`
**Baseline:** 46 tests passed, 0 skipped; no network or credentials used.

## Threat model

The attacker can control invoice/source content, extraction candidates, provider
responses reaching the application, and untrusted serialized objects passed to
public helpers. The attacker cannot modify repository code, the host kernel, or
merchant secrets. Findings requiring control of an environment variable,
application-side authorization object, or privileged caller are marked
conditional rather than treated as unconditional payment compromise.

## Epistemic legend

`CODE FACT` is directly observable. `PLAUSIBLE HYPOTHESIS` is not executed.
`CONFIRMED BY INDUCTION` was reproduced against the live base commit.
`FALSIFIED` was attempted and did not occur.

## Executive summary

| ID | Severity | Level | Module | Finding |
| --- | --- | --- | --- | --- |
| RT-01 | High | Confirmed | Source/MCP | Caller-supplied source objects can fabricate provenance. |
| RT-02 | High conditional | Confirmed | PayPal authorization | Serialized approval is a bearer object without authenticity binding. |
| RT-03 | Medium | Confirmed | Authorization state | Approval and payload construction are replayable locally. |
| RT-04 | High | Confirmed | PayPal reconciliation | Matching amount/currency is not enough to establish provider identity. |
| RT-05 | Medium | Confirmed | PayPal evidence | `NaN` and `Infinity` escape as unhandled exceptions. |
| RT-06 | High conditional | Confirmed | Sandbox client | Manual URL parsing accepts userinfo redirection. |
| RT-07 | Medium | Confirmed | Payout normalization | Duplicate provider item IDs can become completed. |
| RT-08 | High | Confirmed | Source/report/proposal composition | Review-required extraction loses authority at downstream boundaries. |
| RT-09 | Medium conditional | Code fact | Policy | Empty recipient allowlist fails open. |
| RT-10 | Medium | Confirmed | PayPal client | Header idempotency key can differ from payload batch identity. |

## Findings

### RT-01 — Caller-supplied source objects can fabricate provenance

**Severity:** High
**Epistemic level:** CONFIRMED BY INDUCTION
**Bucket:** Software vulnerability / trust-boundary gap

`mcp_server.py:264-282` accepts `sources` directly. `source_workflow.py:35-55`
passes them to `validate_invoice_extraction`, while
`source_ingestion.py:102-129` only checks that `sourceId` and `sourceHash`
exist and checks excerpts against caller-provided `content`. It never proves
that the object came from `list_sources` or that the hash belongs to a file read
by Durin.

**Prediction:** A fabricated source with fabricated content and matching
evidence produces an extracted report without review.

**Induction:** `scripts/redteam_round1.py` supplied `/attacker/invoice.txt`,
`forged-hash`, and matching evidence. Extraction was accepted and the fake hash
was returned as provenance.

**Causal chain:** MCP caller -> forged source envelope -> evidence substring
matches forged content -> report records forged hash -> downstream reader sees
apparently source-backed facts.

### RT-02 — Serialized approval is a bearer object

**Severity:** High conditional
**Epistemic level:** CONFIRMED BY INDUCTION when the caller controls the
authorization object
**Bucket:** Software vulnerability / trust-boundary gap

`paypal_payouts.py:28-36` checks status, execution marker, digest, and expiry,
but does not require a signature, persisted approval record, or even a non-empty
`authorizationId`. A fabricated object with a valid proposal digest was accepted
and produced a payload with `authorizationId: None`.

This is not an unconditional claim that an external user can pay: the missing
piece is the authenticated application-side approval store. It is a real hazard
if an API, MCP, or job queue later accepts approval JSON from an untrusted
caller.

### RT-03 — Approval has no consumable local transition

**Severity:** Medium
**Epistemic level:** CONFIRMED BY INDUCTION
**Bucket:** State-machine vulnerability

`approve_proposal()` returns an authorization without persistence, and
`build_payout_request()` never consumes it. The same pending proposal can be
approved twice and the same authorization can build the same payout payload
twice. PayPal idempotency may limit duplicate remote processing, but it does not
provide local auditability, one-shot authorization, or safe concurrency.

### RT-04 — Reconciliation is not bound to provider identity

**Severity:** High
**Epistemic level:** CONFIRMED BY INDUCTION
**Bucket:** Software vulnerability

`reconcile_provider_evidence()` compares only provider status, amount, and
currency. It does not compare expected payout item ID, transaction ID, receiver,
sender batch ID, supplier, or invoice ID. Evidence with a wrong provider item
identity but matching amount/currency returned `MATCHED`.

The amount check is necessary but insufficient: the event must be bound to the
exact approved obligation and recipient.

### RT-05 — Special numeric provider values escape the boundary

**Severity:** Medium
**Epistemic level:** CONFIRMED BY INDUCTION
**Bucket:** Availability / boundary-validation vulnerability

`paypal_reconciliation._amount()` converts provider input to `Decimal` and only
performs ordinary comparisons. `NaN` raises `decimal.InvalidOperation` and
`Infinity` reaches `TypeError`; `preserve_provider_evidence()` catches only
`ValueError`. A malformed provider response therefore escapes the intended
`REQUIRES_RECONCILIATION` degradation path.

### RT-06 — Sandbox URL validation accepts userinfo redirection

**Severity:** High conditional
**Epistemic level:** CONFIRMED BY INDUCTION if an attacker can influence
`PAYPAL_BASE_URL`
**Bucket:** Software vulnerability / configuration trust boundary

`paypal_client.py:51-55` extracts a hostname using string splitting. The value
`https://api-m.sandbox.paypal.com:443@127.0.0.1` passes validation because the
prefix before the first colon looks approved, while URL parsing treats
`127.0.0.1` as the actual host. `paypal_client.py:107` sends the URL including
Basic OAuth credentials on the token request.

With immutable operator-controlled environment this is hardening. If an attacker
can influence deployment configuration, it becomes credential exfiltration.

### RT-07 — Duplicate provider item IDs can be completed

**Severity:** Medium
**Epistemic level:** CONFIRMED BY INDUCTION
**Bucket:** Reconciliation/state-machine vulnerability

`normalize_payout_response()` does not enforce unique `payout_item_id` or
`transaction_id`. Its completion rule only checks batch `SUCCESS` and every
listed item `SUCCESS`. A batch containing the same item twice returned
`PROVIDER_COMPLETED`.

### RT-08 — Review-required extraction loses authority at composition boundaries

**Severity:** High
**Epistemic level:** CONFIRMED BY INDUCTION
**Bucket:** Software vulnerability / composition break

`source_ingestion.py` marks unsupported evidence for review, but
`source_workflow.py:51-55` stores that marker in a field the supplier engine
does not evaluate. The resulting row can be `READY_FOR_REVIEW` with empty
reasons and no visible `requiresReview` field. `automation.prepare_proposal()`
also ignores an input invoice's `requiresReview` marker.

The same probe found `source_workflow.py:69` counts string `"false"` as truthy,
so `requiresReviewCount` reports one review for a manifest whose value is false.

**Prediction:** Unsupported evidence must remain an explicit review exception and
must not be eligible for an ordinary ready proposal.

**Induction:** An empty evidence map produced a ready row with no reasons, and a
raw invoice containing `requiresReview: true` was accepted by
`prepare_proposal()`.

### RT-09 — Empty allowlist fails open

**Severity:** Medium conditional
**Epistemic level:** CODE FACT
**Bucket:** Business logic / policy assumption

`mcp_server._load_policy()` defaults `approvedRecipients` to `[]`, and
`prepare_proposal()` interprets an empty set as “do not check recipients”. An
arbitrary recipient is accepted into a proposal. The current global human
approval boundary prevents autonomous payment, so severity increases if an
auto-execution path is added or “ready” is treated as verified.

### RT-10 — Header idempotency key can diverge from payload identity

**Severity:** Medium
**Epistemic level:** CONFIRMED BY INDUCTION
**Bucket:** Business logic / idempotency boundary

`PayPalSandboxClient.create_payout()` accepts a caller-supplied
`sender_batch_id` for `PayPal-Request-Id` but does not verify it matches
`payload.sender_batch_header.sender_batch_id`. The probe submitted `payload-key`
with header key `header-key`. Retries can be reasoned about under one identity
while PayPal deduplicates under another.

## Discarded vectors

| Vector | Result | Why it failed |
| --- | --- | --- |
| Production PayPal endpoint | FALSIFIED | Current validator rejects `api-m.paypal.com`. |
| Change amount after approval | FALSIFIED | Proposal digest mismatch rejects it. |
| Extraction field `approve_payment` | FALSIFIED | Unauthorized candidate fields are rejected. |
| Malformed invoice amount | FALSIFIED | MCP proposal path fails closed. |
| Exact amount/currency mismatch | FALSIFIED | Returns `RECONCILIATION_REQUIRED`. |
| Tracked secrets in current tree | FALSIFIED for snapshot | No secret found; `.env` is ignored and only the template is tracked. |
| Real PayPal operation | NOT EXECUTED | No credentials or provider network were used. |

## Test integrity

- Baseline: 46 tests passed, 0 skipped.
- Negative control: mutating the exact reconciliation comparison to `if False`
  caused `test_currency_or_amount_mismatch_is_not_posted` to fail.
- Blind-spot mutation: replacing `requiresReviewCount` with `0` left all 46
  tests green. The suite had no oracle for that metric.
- Fake provider transports verify local assumptions, not PayPal live behavior.
- Concurrency, crash recovery, authenticated application endpoints, real Sandbox
  accounts, and secret rotation were not tested.

## Recommendations — no fixes applied in this audit

1. Make source objects server-owned: ingest by source ID or re-read/hash the
   authorized path; never accept caller-supplied content as provenance.
2. Make approval a persisted, authenticated, one-shot record bound to the exact
   proposal, approver, expiry, and execution attempt.
3. Bind reconciliation to expected provider batch/item/transaction and recipient
   identity; reject duplicate IDs and unknown cardinality.
4. Reject non-finite and over-precision money at the provider boundary.
5. Parse `PAYPAL_BASE_URL` with `urllib.parse.urlsplit`, reject userinfo, and
   enforce exact Sandbox or explicit loopback test mode.
6. Propagate `requiresReview` into deterministic exclusion/review state and make
   proposal preparation reject review-required inputs.
7. Require an explicit recipient allowlist for execution and make payload/header
   share one idempotency identity.
