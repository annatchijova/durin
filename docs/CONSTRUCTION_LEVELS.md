# Durin construction levels

This document uses destination-driven construction. A level is a complete,
useful state of Durin, not a technical phase and not a feature inventory.

Every level must be useful on its own, compatible with the final product, and
built with the final authority, provenance, financial, recovery, and uncertainty
invariants already present. If time runs out, construction stops at the highest
complete level reached. It does not downgrade a level into a disposable demo.

The post-hackathon plan continues beyond the level reached during the event. We
do not need to reach the last level now.

## Destination

Durin is an AI-assisted operations system for merchants with many suppliers.
It organizes invoices, contracts, emails, supplier identity, payment terms,
exceptions, and PayPal payout operations into an explainable workflow.

The agent investigates and automates repetitive organization. Deterministic code
owns amounts, currencies, identity, matching, balances, policy checks, and
state transitions. A merchant remains the authority for any monetary action.

## Financial direction

The primary domain is `PAYABLE`: obligations owed by a merchant to suppliers.
This is the pain inherited from Vértice: organizing many providers and deciding
what is ready, blocked, duplicated, contradictory, overdue, or already paid.

`RECEIVABLE`—customer invoices and collections—is a separate future domain. It
must not share a balance formula or overloaded status field with `PAYABLE`.

## Invariants inherited by every level

### Financial correctness

- No binary floating-point values in financial decisions.
- Amounts use integer minor units or a pinned exact decimal representation,
  always paired with an ISO currency.
- One obligation or operation cannot be counted twice.
- Currency conversion requires a sourced rate, effective time, and explicit
  conversion event.

### Evidence provenance

Every extracted or observed fact carries:

```text
source
source_hash
source_location
field_name
evidence_excerpt
observed_at
extraction_method
extractor_version
extracted_value
confidence_signal
validation_status
requires_review
```

Model confidence is an auxiliary signal. It is not a calibrated probability and
never authorizes a payment or confirms reconciliation by itself.

### Authority separation

Emails, contracts, invoices, PayPal responses, and MCP output are data, not
instructions. Retrieved content cannot grant the agent new authority. The agent
cannot change policy, approve a proposal, capture funds, or send money.

### Idempotency and recovery

Retries cannot create a second operation or accounting entry. A provider timeout
after submission becomes `UNKNOWN` and requires recovery from the provider rather
than a blind retry.

### Epistemic uncertainty

Missing, contradictory, stale, or ambiguous evidence remains visible as
`REQUIRES_REVIEW` or `INSUFFICIENT_EVIDENCE`; it never becomes silent success.

## Financial contracts

The payable balance is derived only from recognized events:

```text
outstanding =
    recognized_obligation
    - recognized_settlements
    + recognized_reversals
    - authorized_adjustments
```

A provider operation reduces an obligation only when supplier identity,
recipient, amount, currency, reference, direction, and recognition policy match.
A return or reversal increases the outstanding amount only when it reverses a
previously recognized settlement. A credit requires provenance and authorization.

States remain orthogonal:

| Dimension | Examples |
| --- | --- |
| Obligation | `OPEN`, `PARTIALLY_SATISFIED`, `SATISFIED`, `CANCELLED`, `DISPUTED` |
| Provider operation | Raw PayPal status, preserved without invented equivalence |
| Reconciliation | `MATCHED`, `PARTIALLY_MATCHED`, `UNMATCHED`, `AMBIGUOUS` |
| Review | `NOT_REQUIRED`, `REQUIRED`, `APPROVED`, `REJECTED` |

An approval binds to an immutable proposal containing the obligation, recipient,
amount, currency, operation, policy version, evidence references, identifier,
and expiry. Any material change invalidates the approval.

## Complete levels

### Level 1 — AI supplier operations intelligence

**Complete product state:** A merchant provides authorized email exports,
attachments, supplier invoices, contracts, and policy. The AI extracts candidate
facts with provenance. Deterministic automation organizes the supplier batch,
detects duplicates, conflicts, recipient typos, price anomalies, limits, and
missing evidence, then produces an exact metrics and exception report.

The complete flow is:

```text
authorized emails + contracts + invoices + policy
        -> AI extraction with provenance
        -> supplier normalization and deterministic preflight
        -> duplicate/conflict resolution and review queue
        -> exact metrics, report, and exportable operations rows
```

Level 1 may use imported operation records as observations. It does not pretend
that a provider operation occurred merely because an invoice says so. It is a
complete merchant intelligence product without live PayPal execution, not a
technical fragment waiting to be replaced.

**Required capabilities:** supplier organization, invoice identity, evidence
fields, duplicate detection, typo detection, price-history alerts, limits,
partial/mismatched/pending operation detection, overdue items, batch totals,
reports, and human review markers.

**Adversarial gate:** prompt injection inside an invoice, contradictory contract
term, duplicate attachment, altered source hash, duplicate invoices, two
operations for one obligation, partial operation, mismatched currency,
recipient typo, conflicting supplier identity, pending operation, malformed
amount, and missing evidence.

**Standalone value:** the merchant can turn a messy supplier inbox into an
evidence-backed operational report and know what is ready, blocked, duplicated,
contradictory, overdue, or unresolved.

### Level 2 — PayPal Payouts integration

**Mandatory complete product state:** Level 1 runs against the selected PayPal
Sandbox payout capability. Durin reads and normalizes real provider operations,
prepares immutable payout proposals, waits for explicit merchant approval,
submits only the approved operation, recovers safely from unknown outcomes, and
updates the supplier report.

The complete flow is:

```text
merchant sources + AI report
        -> immutable payout proposal
        -> merchant approval
        -> PayPal Payout operation
        -> provider status and recovery
        -> deterministic reconciliation and updated report
```

No credential reaches the agent. PayPal status remains provider data. A payout
may be `Pending`, `Success`, `Unclaimed`, `Refunded`, `Failed`, `On Hold`,
`Blocked`, `Denied`, or `Returned`; Durin does not collapse these states into a
boolean or claim final settlement without the correct evidence.

**Adversarial gate:** timeout after submission, repeated lookup, duplicate
response, pending payout, returned payout, provider API error, changed recipient,
changed amount after approval, replayed approval, and credentials exposed to the
agent.

**Standalone value:** the merchant can organize, approve, execute, recover, and
reconcile real PayPal payout activity for many suppliers.

### Level 3 — Post-hackathon improvements

Each post-hackathon improvement must still be a complete end-to-end product
state, not a technical phase. Possible destinations include additional email
connectors, recurring reports, richer PayPal operations, supplier portals,
multi-currency support, and the independent `RECEIVABLE` domain.

`RECEIVABLE` is not implemented by renaming `PAYABLE`; its evidence and balances
remain independent. It can be added without invalidating the supplier product.

## Current position

The repository contains the deterministic supplier engine, MCP, source hashing,
provenance-preserving extraction validation, a source-to-report orchestrator,
report persistence, fixtures, agent-boundary documentation, a real OpenAI
extraction pipeline with a draft/review ledger and cross-source contradiction
detection, a read-only IMAP source connector (implemented, not yet run against a
real mailbox), and a PayPal Payouts adapter confirmed live against the real
Sandbox (OAuth, create/get payout, idempotency, IN_FLIGHT recovery, and an
UNCLAIMED exception) — see `docs/AI_EXTRACTION.md` and `docs/PAYPAL_ADAPTER.md`
for the evidence. The end-to-end agent-usable MCP flow (sources -> extraction ->
report -> proposal -> sealed proposal) is pinned by
`test_mcp_flow_integration.py`. Two red-team rounds ran against tonight's
additions (`docs/RED_TEAM_AUDIT_2026-11-09.md`); no exploitable finding survived
induction, three hygiene fixes landed, and one architectural note (the IMAP
connector's authorization boundary is the mailbox itself) is documented rather
than code-fixed.

It is not Level 1 yet: the authorized source connector has code but no live
mailbox test, and the OpenAI extraction provider, while real and live-tested,
has not been run against a merchant's actual authorized source batch. Level 2
PayPal integration is mandatory after Level 1 and is not optional scope; its
Sandbox execution path is now live-confirmed, but the MCP-driven approval flow
that would drive it from an agent session end to end is still assembled from
pieces tested individually, not run as one continuous live session.

A frontend now exists (`frontend/`, Next.js, bilingual en/es) behind
`api_server.py` (FastAPI). Live-tested end to end through the browser: real
OpenAI extraction, a real cross-source contradiction (the model swapped
supplier/recipient between two sources, caught by `CONFLICTING_SUPPLIER_IDENTITY`
and visibly distinguished from reconciled rows), proposal, approval, and a
real PayPal Sandbox submission reconciled to `SUCCESS`. It is a working
first product surface, not a mockup -- but has a merchant-identity gap: the
`approverId` on the approval step is free-text, not an authenticated
session, so it does not yet carry real authority. Still open: a non-demo
auth boundary for the approval action, and a real-time view of a payout
still `PENDING` (the UI currently requires a manual "refresh" click).

## Open constraints

| Constraint | State | Revisit trigger |
| --- | --- | --- |
| First authorized email/source boundary | IMAP connector implemented (`source_connector_imap.py`, read-only select, no flag/move/delete, shares `source_ingestion.build_source_record` with the filesystem path); not yet run against a real mailbox — no IMAP credentials were available to test live | Required to complete Level 1. |
| AI extraction provider and structured output contract | OpenAI extractor, draft ledger, and cross-source/policy contradiction detection implemented (see `docs/AI_EXTRACTION.md`); not yet run against a real authorized source batch | Required to complete Level 1. |
| PayPal Payouts Sandbox access and capability | Live-tested: OAuth, `create_payout`, and `get_payout` confirmed against the real Sandbox (see docs/PAYPAL_ADAPTER.md); the MCP-driven approval and source-connector flow around it is still open | Required to start Level 2. |
| Payout settlement evidence | Open, unresolved | Resolve before claiming final settlement. |
| Currency conversion policy | Open, unresolved | Required before multi-currency supplier batches. |

These are open constraints, not completed features and not silently discarded
requirements.
