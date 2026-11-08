# Durin construction levels

This document uses destination-driven construction. A level is a complete,
useful state of Durin, not a technical phase and not a feature inventory.

Every level must be useful on its own, compatible with the final product, built
with the final authority/provenance/financial/recovery invariants already
present, independently adversarially reviewed, and safe to stop at without
making the previous level disposable.

The post-hackathon plan continues beyond any level reached during the event. The
goal is not to reach the last level in four days. The goal is to finish the
highest complete level that time and access allow.

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

PayPal Payouts is the planned execution adapter for the primary domain. Until
that adapter is implemented, Durin can still provide a complete offline
supplier-operations level using imported operation records.

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

### Level 1 — Supplier operations desk

**Complete product state:** A merchant imports a bounded batch of supplier
invoices and operation records, and receives a usable operations report without
calling an external payment provider.

The complete flow is:

```text
supplier records + invoices + policy + operation records
                         ->
normalization + preflight + duplicate/conflict detection
                         ->
supplier queue + exact metrics + exception report
```

It preserves the Vértice workflow: supplier organization, invoice identity,
recipient checks, duplicate detection, typo detection, price-history alerts,
limits, partial/mismatched operations, overdue items, batch totals, and
exportable report rows. It must not claim that an operation happened merely
because an invoice says so.

**Adversarial gate:** duplicate invoices, two operations for one obligation,
partial operation, mismatched currency, recipient typo, conflicting supplier
identity, pending operation, malformed amount, and missing evidence.

**Standalone value:** the merchant can organize a supplier batch and know what is
ready, blocked, duplicated, contradictory, or unresolved.

### Level 2 — AI source-to-report operations desk

**Complete product state:** A merchant provides authorized email exports,
attachments, invoices, and contracts. The agent extracts candidate facts,
preserves evidence, runs the Level 1 engine, and produces a report with human
review markers.

The complete flow is:

```text
authorized business sources
        -> AI extraction with provenance
        -> deterministic supplier preflight and reconciliation
        -> report, metrics, conflicts, and review queue
```

Documents are data, never instructions. The agent can resolve duplicates and
conflicts only through explicit deterministic rules; ambiguous cases remain
visible for review.

**Adversarial gate:** prompt injection inside an invoice, contradictory contract
term, duplicate attachment, altered source hash, missing excerpt, low-confidence
field, and extractor output containing unauthorized fields.

**Standalone value:** the merchant can turn a messy supplier inbox into an
evidence-backed operational report without manually organizing every document.

### Level 3 — PayPal Payouts operations desk

**Complete product state:** The same supplier workflow reads real PayPal Sandbox
payout operations, preserves provider statuses, reconciles them with obligations,
and recovers safely from retries and unknown outcomes.

The complete flow is:

```text
merchant sources + PayPal Payouts activity
        -> evidence and provider-state normalization
        -> deterministic supplier reconciliation
        -> report + explicit exceptions + recovery state
```

No credential reaches the agent. PayPal status is preserved as provider data;
Durin does not invent settlement claims. A payout may be `Pending`, `Success`,
`Unclaimed`, `Refunded`, `Failed`, `On Hold`, `Blocked`, `Denied`, or `Returned`
without those states being collapsed into one boolean.

**Adversarial gate:** timeout after submission, repeated lookup, duplicate
response, pending payout, returned payout, provider API error, changed recipient,
and credentials exposed to the agent.

**Standalone value:** the merchant can organize and reconcile real PayPal payout
activity for many suppliers.

### Level 4 — Merchant-authorized payment operations

**Complete product state:** From the Level 3 report, the merchant can approve an
immutable payout proposal. Durin submits only the authorized operation through
the PayPal capability adapter, records the provider result idempotently, and
updates the report.

The complete flow is:

```text
supplier obligation + evidence
        -> immutable proposal
        -> merchant approval
        -> PayPal Payout operation
        -> recovery + reconciliation + report
```

The agent cannot approve its own proposal. A changed amount, beneficiary,
currency, operation, policy, or evidence set requires a new approval.

**Adversarial gate:** replayed approval, changed beneficiary, changed amount,
duplicate execution, provider timeout, partial result, revoked policy, and agent
self-approval.

**Standalone value:** the merchant can move from organized supplier work to
controlled PayPal execution without surrendering monetary authority.

### Level 5 — Receivables extension

**Complete product state:** Durin adds customer invoices and PayPal collections as
a separate end-to-end domain, with its own operation model, reconciliation rules,
reports, and review states.

`RECEIVABLE` is not implemented by renaming `PAYABLE`; its evidence and balances
are independent. This level can be built post-hackathon without invalidating the
supplier product.

**Adversarial gate:** duplicate capture, partial capture, refund after recognition,
unmatched customer payment, ambiguous match, fee omission, pending capture, and
unsupported settlement claim.

**Standalone value:** the merchant can analyze both outgoing supplier operations
and incoming customer collections without confusing their semantics.

## Current position

Durin currently has the bounded MCP, pure automation engine, supplier preflight,
metrics, and agent-boundary documentation. These are the core of Level 1, but
Level 1 is not complete until the canonical supplier records, report persistence,
and end-to-end batch report are connected.

## Open constraints

| Constraint | State | Revisit trigger |
| --- | --- | --- |
| PayPal Payouts Sandbox access and capability | Open, unresolved | Validate before Level 3. |
| Email provider and consent boundary | Open, unresolved | Select the first authorized source for Level 2. |
| Payout settlement evidence | Open, unresolved | Map PayPal responses before claiming final settlement. |
| Currency conversion policy | Open, unresolved | Required before multi-currency supplier batches. |

These are open constraints, not completed features and not silently discarded
requirements.
