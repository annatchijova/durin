# Red-Team Fix Audit — 2026-11-08

## Scope

This audit reviews the fixes applied after
`docs/RED_TEAM_VARIANT_AUDIT_2026-11-08.md`. It was performed against the live
working tree before commit, with an independent read-only reviewer used for the
second pass.

Skills applied: `audit-before-patch`, `red-team-auditing`, `variant-analysis`,
`falsifiable-testing`, `deterministic-core`, `agent-trust-boundaries`,
`atomic-state-mutation`, and `honest-degradation`.

No network access, PayPal credentials, real provider calls, deployments, or
transactions were used.

## Verification performed

- `python3 -m unittest discover -s . -p 'test_*.py'`: **59 passed, 0 failed,
  0 skipped**.
- `python3 scripts/redteam_round1.py`: executed; prior spoofing, untrusted
  evidence, malformed numeric, URL, and empty-allowlist vectors now fail closed.
- `python3 scripts/redteam_variant_round.py`: executed; sibling entry points
  were re-exercised after the fixes.
- `python3 -m compileall -q .`: passed.
- `git diff --check`: passed.
- Level 1 offline report: executed successfully; pending provider observations
  remain explicit and no payment is claimed.

## Fixes confirmed by induction

| Invariant | Verification result |
| --- | --- |
| Source objects must be attested and content/hash consistent | Forged and mutated sources rejected. |
| Extracted values must occur in their excerpts | Generic excerpts no longer support fabricated values. |
| Source IDs and source cardinality are bounded | Duplicate IDs and oversized workflows rejected. |
| Contract sources cannot be extracted as invoices | Rejected at extraction boundary. |
| Review-required invoices cannot enter proposals | `REQUIRES_SOURCE_REVIEW` excludes them. |
| Allowlist and base currency apply across sibling engines | Empty allowlists and incompatible currencies fail closed. |
| Provider success requires preserved, bound evidence | Declared IDs without attested evidence are unverified. |
| Provider evidence is bound to invoice and batch identity | Evidence for another obligation is rejected. |
| Provider IDs are present and unique | Missing or duplicate PayPal IDs do not complete a batch. |
| Proposal totals and item identities are coherent | Negative, exponential, mismatched, and duplicate items reject. |
| Authorization proof covers authorization identity | Mutating `authorizationId` invalidates the proof. |
| Execution state and approval time are coherent | Executed proposals and pre-approval observations reject. |
| Non-finite amounts and timeouts are bounded | `NaN`, `Infinity`, and naive timestamps fail closed. |
| Request idempotency identities agree | Payload and `PayPal-Request-Id` must match. |
| Confirmed submission cannot repeat in one process | Successful client submission consumes the authorization. |
| Request construction is recoverable after transport failure | Consumption occurs after a successful provider response, not while building. |
| In-process submission check/send/consume is serialized | A process-wide lock prevents the tested thread race. |

## Residual findings

### FIX-AUDIT-01 — Durable replay protection is still missing

**Severity:** High, conditional on multi-process deployment  
**Status:** Confirmed by induction

Consumed authorizations are held in the process-local
`_CONSUMED_AUTHORIZATIONS` set. The stable `DURIN_AUTHORIZATION_KEY` makes
proofs verifiable across workers, but it does not share consumed state.

A second worker can therefore accept the same authorization unless the caller
provides a durable, shared ledger around the submission boundary. The current
process-wide lock does not cross process boundaries.

The application must not use the current in-memory consumption guard as the sole
replay control for a multi-worker production deployment.

### FIX-AUDIT-02 — Approval uniqueness is not durable

**Severity:** High, conditional on multi-process deployment  
**Status:** Confirmed by induction

`approve_proposal()` still does not persist a proposal transition. A proposal
can receive multiple approvals if the caller invokes it again, especially after
a restart or from another worker. The proof is valid, but validity is not the
same as single-use state.

### FIX-AUDIT-03 — Attestation is integrity, not external provider authenticity

**Severity:** High, conditional on the caller reaching the attestation helper  
**Status:** Plausible boundary limitation

`providerEvidence` now has an HMAC and is bound to invoice and batch identity.
This prevents an untrusted serialized object from being modified silently.
It does not independently prove that the original provider response came from
PayPal; that guarantee depends on the authenticated PayPal client boundary and
secret handling. A caller with access to the attestation key could mint a
valid-looking evidence object.

### FIX-AUDIT-04 — Stable secret configuration is operator-dependent

**Severity:** Medium operational  
**Status:** Confirmed by induction

Source, authorization, and provider-evidence keys are process-random unless the
operator sets `DURIN_SOURCE_ATTESTATION_KEY`, `DURIN_AUTHORIZATION_KEY`, and
`DURIN_PROVIDER_EVIDENCE_KEY`. `.env.example` now lists them, but the system
does not enforce their presence. A restart without stable keys makes previously
serialized artifacts unverifiable.

## Falsified vectors

- Mutating only `authorizationId` while retaining the old proof.
- Forged provider evidence without an attestation.
- Attested evidence bound to a different invoice.
- Mutating `source["observedAt"]` after ingestion.
- Duplicate provider IDs and missing provider IDs.
- Negative or exponential proposal amounts.
- Empty allowlists in both proposal and supplier-operation entry points.
- Two submission attempts in the same process after a successful response.
- Two in-process submission threads passing the authorization check concurrently.

## Decision

**The local security boundary is materially improved and regression-tested, but
the PayPal execution path is not yet production-ready for multiple workers.**
Before real execution, add a durable shared authorization/submission ledger,
make stable key configuration mandatory, and keep the authenticated PayPal
client as the only producer of provider evidence.

No claim is made that a PayPal payment occurred.
