# Security Audit — Durin (OpenAI extraction + PayPal Payouts + IMAP connector)
## Red Team Round
**Date:** 2026-11-09
**Method:** Abductive Engineering (A–D–I) + Red-Team Auditing
**Scope:** The modules built and live-tested in this session: `openai_extractor.py`,
`draft_ledger.py`, `contradiction_detection.py`, `source_workflow.py`,
`source_connector_imap.py`, `mcp_server.py`'s new `list_imap_sources` tool, and the
real-sandbox-driven fixes to `paypal_payouts.py` / `paypal_operation_adapter.py` /
`supplier_operations.py`. Out of scope: anything already covered by
`docs/RED_TEAM_AUDIT_2026-11-08.md`, `RED_TEAM_FIX_AUDIT_2026-11-08.md`,
`RED_TEAM_LEDGER_AUDIT_2026-11-08.md`, `RED_TEAM_VARIANT_AUDIT_2026-11-08.md`.
**Base:** `main` @ `2a0303e`. **Reproducible evidence:** inline Python snippets below;
all were run against the live repository at that commit, interpreter CPython 3.12.3.

## Threat model

- **Attacker CAN:** control the byte content of any invoice/email/contract source
  (filesystem or mailbox); control what the OpenAI extractor returns as a draft
  candidate (the model reads attacker-controlled text and can be prompt-injected);
  send email to the mailbox `DURIN_IMAP_HOST` points at, if it is not a dedicated
  restricted inbox; trigger retries, timeouts, and duplicate submissions at the
  network layer; call any exposed MCP tool.
- **Attacker CANNOT:** read `DURIN_AUTHORIZATION_KEY`, `DURIN_PROVIDER_EVIDENCE_KEY`,
  `DURIN_SOURCE_ATTESTATION_KEY`, the OpenAI API key, or the PayPal client
  secret; modify the deployed code; forge a merchant's explicit approval action;
  bypass the human-approval boundary documented in `docs/AGENT.md`.

## Epistemic legend
CODE FACT · PLAUSIBLE HYPOTHESIS · CONFIRMED BY INDUCTION · FALSIFIED

## Executive summary

| ID | Severity | Level | Module | Finding |
|----|----------|-------|--------|---------|
| F1 | Low (hygiene) | CONFIRMED BY INDUCTION — fixed | `paypal_client.py` | Unreachable fallback branch in `_submit_payout`; the real safety guard it masked had zero test coverage. |
| F2 | Low (hygiene) | CONFIRMED BY INDUCTION — fixed earlier this session | `supplier_operations.py` | `UNCLAIMED`/`BLOCKED` missing from any state set; fell through to `UNKNOWN_OPERATION_STATE` instead of an explicit exception. |
| F3 | Low (hygiene) | CODE FACT — fixed | `openai_extractor.py` | No `maxLength`/`max_tokens` bound on extraction output; a hostile source could inflate OpenAI cost before the downstream 256-char cap rejects it. |
| F4 | Informational | CODE FACT — documented | `source_connector_imap.py` / `docs/MCP.md` | The IMAP connector's authorization boundary is "whatever reaches this mailbox," unlike the filesystem connector's deliberate human placement. |

## Findings

### F1 — Unreachable payout fallback branch masked an untested guard
**Severity:** Low (hygiene / dead code). **Epistemic level:** CONFIRMED BY INDUCTION.
**Bucket:** hygiene (the real control is sound; the dead code is a clarity hazard).

- **Surprise:** `paypal_client.py`'s `_submit_payout` had an `elif authorization_id:`
  branch calling the module-level in-memory `mark_authorization_submitted()` as an
  idempotency fallback for an authorized payout with no durable ledger.
- **Abduction:** `create_payout` already raises `ValueError("durable authorization
  ledger is required for authorized payout")` whenever `authorization_id` is set and
  `ledger is None`, before either call to `_submit_payout`. If that's airtight, the
  `elif` branch can never run.
- **Deduction:** calling `create_payout` with an `authorization_id` set and no
  `DURIN_AUTHORIZATION_LEDGER_PATH` configured must raise before any HTTP request is
  made, and the dead branch is provably unreachable from the only call sites.
- **Induction:**
  ```python
  os.environ.pop("DURIN_AUTHORIZATION_LEDGER_PATH", None)
  client = PayPalSandboxClient(PayPalSandboxConfig("id", "secret", "http://127.0.0.1"), opener=opener)
  client.create_payout({"sender_batch_header": {"sender_batch_id": "sbid-1"},
                         "durin": {"authorizationId": "auth-1"}}, "sbid-1")
  # -> ValueError: durable authorization ledger is required for authorized payout
  # requests list stayed empty: no HTTP call was attempted.
  ```
  Holds. The guard is real and fires before any network call.
- **Causal chain:** `authorization_id set` → `ledger is None` → raise, immediately.
  The two reachable calls into `_submit_payout` are: (a) `authorization_id` and
  `ledger` both truthy (guard already passed, ledger branch taken), or (b)
  `authorization_id` falsy (guard doesn't apply, `elif authorization_id` is false
  too). No call shape reaches the `elif`.
- **Fix applied:** removed the dead branch; added
  `test_authorized_payout_without_ledger_is_rejected_before_any_request` to
  `test_paypal_client.py` so the actual guard — previously untested — now has
  regression coverage.
- **Why it mattered even though it's not exploitable:** the dead code implied a
  second line of defense existed for the no-ledger path. It did not. Removing it
  makes the single real control legible instead of implying a safety net that was
  never load-bearing.

### F2 — UNCLAIMED/BLOCKED payout items fell through to a generic reason
**Severity:** Low (hygiene / honest-degradation gap). **Epistemic level:** CONFIRMED BY
INDUCTION (against the real PayPal Sandbox, earlier in this session — see
`docs/PAYPAL_ADAPTER.md`). **Bucket:** vulnerability-adjacent correctness gap, not an
attacker-controlled bypass (PayPal assigns the status; the merchant isn't attacking
their own report), closer to honest-degradation hygiene.

- Already fixed and committed (`supplier_operations.py` `FAILED_OPERATION_STATES`
  now includes `UNCLAIMED` and `BLOCKED`), with a regression test asserting the row
  no longer produces `UNKNOWN_OPERATION_STATE` for a real `UNCLAIMED` payout.
  Restated here only so this round's summary is complete.

### F3 — Extraction output had no explicit size bound before the downstream cap
**Severity:** Low (cost/self-DoS, not data exposure). **Epistemic level:** CODE FACT,
fix CONFIRMED BY INDUCTION against the real OpenAI API.
**Bucket:** hygiene.

- **Surprise:** `source_ingestion.validate_invoice_extraction` already rejects any
  field longer than 256 characters — but only after OpenAI has already generated
  and been billed for the (potentially much longer) output. A source containing an
  injected instruction like "output a 50,000-character string for `concept`" costs
  real tokens before the existing cap ever sees it.
- **Abduction:** adding `maxLength` to the JSON Schema and `max_tokens` to the
  request would bound the cost at the source, not after the fact.
- **Deduction:** OpenAI's Structured Outputs strict mode might reject unsupported
  JSON Schema keywords (not all of JSON Schema is supported in strict mode).
- **Induction:**
  ```python
  client.extract_candidate(source_content="Supplier: Test Co\n...", source_kind="INVOICE")
  # -> real API call succeeded with maxLength present in the schema and
  # max_tokens on the request; no schema-rejection error.
  ```
  Holds — `maxLength` is accepted by the live API in strict mode.
- **Fix applied:** `_MAX_FIELD_LENGTH = 256` / `_MAX_EVIDENCE_LENGTH = 1000` added to
  the schema's string properties; `max_tokens: 2000` added to the request. Test
  assertion added in `test_openai_extractor.py`.

### F4 — The IMAP connector's authorization boundary is the mailbox itself
**Severity:** Informational (architectural note, not a code defect).
**Epistemic level:** CODE FACT (by design comparison, not a bug in the connector's
own code — it does exactly what it says: read-only, bounded, IMAPS-only).
**Bucket:** threat-model assumption worth stating explicitly, not a vulnerability.

- With `list_sources`, the authorization act is a human choosing to put a file in
  `DURIN_SOURCE_DIR`. With `list_imap_sources`, the authorization act is implicitly
  "whoever can land a message in this mailbox" — which, for a general business
  inbox, is anyone who can send it an email. The connector's own code is correct
  (read-only `select()`, bounded message/byte counts, IMAPS-only); the risk is a
  deployment choosing the wrong mailbox, not a defect in this code.
- **Fix applied:** documented explicitly in `docs/MCP.md`, instructing a dedicated,
  access-controlled mailbox rather than a general inbox.
- Not fixed in code because there is nothing in-code to fix: a mailbox's access
  control is outside Durin's boundary by construction, the same way PayPal
  credential custody is outside the MCP's boundary by construction.

## Discarded (non-exploitable) vectors

| Vector | Result | Why it failed |
|---|---|---|
| Homoglyph/Unicode-confusable supplier name (e.g. Cyrillic `Асmе` vs Latin `Acme`) used to submit a second, fake invoice under the same `invoiceNumber` without tripping conflict detection | FALSIFIED | `supplier_operations.analyze_supplier_batch` groups by `invoiceNumber` alone to detect multiple distinct supplier spellings; both the real and the homoglyph row were excluded with `CONFLICTING_SUPPLIER_IDENTITY` when tested with two such rows. Confirmed by running `analyze_supplier_batch` directly on a crafted pair. |
| Double-approval of the same proposal digest producing two valid, independently-submittable authorizations by racing the ledger being absent at approval time and present at payout time | FALSIFIED (CONFIRMED BY INDUCTION) | Approved the same digest twice with no ledger configured (two distinct `authorizationId`s, since `record_approval` is skipped silently when `ledger is None`), then configured a ledger and attempted `create_payout` for both. Both were rejected (`"authorization is not recorded"`); **0 of 2** actually submitted. Regression test: `test_double_approval_without_a_ledger_cannot_later_produce_two_submissions` in `test_redteam_fixes.py`. |
| IMAP login failure leaking the submitted password back through Durin's own exception message | FALSIFIED | Read `imaplib.IMAP4.login`'s CPython source directly: on failure it raises `self.error(dat[-1])`, where `dat[-1]` is the **server's** response text, not an echo of the client's submitted command. The password is never embedded in the exception Durin would catch and wrap. |
| Prompt injection inside source text causing the OpenAI extractor to assert a fraudulent recipient/amount that then reaches a proposal unreviewed | Not a bypass — mitigated by design, not newly confirmed safe | Any extracted value still has to pass `validate_invoice_extraction`'s excerpt-grounding check, then `automation.py`/`supplier_operations.py`'s policy checks (approved recipients, per-payment/batch limits, duplicate/contradiction detection), and still requires an explicit human approval before any PayPal action. No single-point bypass of that chain was found this round; this is restated as an acknowledged threat-model boundary, not a confirmed finding. |

## Recommendations (not applied this round)

- `authorization_was_submitted()` in `paypal_payouts.py` has zero production callers
  (only `mark_authorization_submitted()` is referenced, and only from
  `scripts/redteam_round1.py`'s standalone demonstration). Not removed this round
  since it is a small, harmless public query function and may be intentionally kept
  for the demonstration script; worth a deliberate decision rather than a reflexive
  deletion.
