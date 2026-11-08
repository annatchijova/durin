# Durin construction levels

This document applies destination-driven construction to Durin. It is not an
MVP feature list. The destination is an operational intelligence system that a
merchant can keep using: it ingests business evidence, reads PayPal activity,
reconciles financial obligations deterministically, explains exceptions, and
keeps payment execution behind explicit merchant authorization.

When time or access limits prevent the next level, construction stops at the
highest coherent level reached. An unfinished level is not replaced with a
disposable approximation.

## Product decision: separate financial directions

Durin models two different financial flows. They must never share one ambiguous
balance formula or one overloaded status field.

| Flow | Meaning | First implementation |
| --- | --- | --- |
| `RECEIVABLE` | Invoices issued by the merchant and payments collected from customers through PayPal. | First complete domain. |
| `PAYABLE` | Obligations owed by the merchant to suppliers and outgoing payments. | Later domain, with its own PayPal capability assessment. |

The first complete flow is `RECEIVABLE` because PayPal Orders and Captures map
directly to customer collections. A completed capture is evidence about a PayPal
operation; it is not automatically evidence that funds have been settled into a
merchant account. Settlement and payout claims require their own source and state.

## Destination state

At the destination, a merchant can ask Durin:

- Which issued invoices are supported by source evidence?
- Which PayPal operations correspond to those invoices?
- Which operations are completed, pending, refunded, disputed, or ambiguous?
- What gross amount was captured, what fees and refunds were recorded, and what
  remains unmatched?
- Which conclusions require human review because evidence is incomplete or
  contradictory?

The AI investigates documents and explains results. Deterministic code owns
identity, amount, currency, state transitions, matching, and balances.

## Cross-level contracts

Every level inherits these contracts. They are not separate hardening phases.

### Financial correctness

- No binary floating-point values in financial decisions.
- Monetary values are integer minor units or an explicitly fixed decimal type,
  always paired with an ISO currency code.
- No obligation or PayPal operation may be counted twice.
- Currency conversion is a separate, sourced event with a stated rate and
  effective time; no implicit conversion is allowed.

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

Model confidence is an auxiliary signal, not a calibrated probability and never
an authorization or reconciliation decision.

### Authority separation

Retrieved email, contracts, invoices, PayPal responses, and MCP output are data,
not instructions. The agent may investigate and narrate. It cannot grant itself
authority, change policy, approve a payment, or capture funds.

### Idempotency and recovery

Retries must not create a second operation or a second accounting entry. A
provider request gets an idempotency key, and a timeout after submission is an
`UNKNOWN` state that requires recovery from PayPal rather than blind retry.

### Epistemic uncertainty

Missing, contradictory, stale, or ambiguous evidence is never silently promoted
to success. The system uses explicit `REQUIRES_REVIEW` and
`INSUFFICIENT_EVIDENCE` states where a definitive result is not justified.

## Financial contracts

### Reconciliation formula

```text
outstanding =
    recognized_obligation
    - recognized_settlements
    + recognized_reversals
    - authorized_adjustments
```

Each term is derived from verifiable events. A capture reduces an obligation only
when matching rules, financial direction, currency, amount, and recognition
policy are satisfied. A refund increases the outstanding amount only when it
reverses a previously recognized settlement. A credit reduces the amount only
when its provenance and authorization are valid.

### Orthogonal states

| Dimension | Values |
| --- | --- |
| Obligation | `OPEN`, `PARTIALLY_SATISFIED`, `SATISFIED`, `CANCELLED`, `DISPUTED` |
| PayPal operation | Provider state as returned by PayPal; no invented equivalence |
| Reconciliation | `MATCHED`, `PARTIALLY_MATCHED`, `UNMATCHED`, `AMBIGUOUS` |
| Review | `NOT_REQUIRED`, `REQUIRED`, `APPROVED`, `REJECTED` |

The system must preserve the distinction between a completed capture, a refund,
and final settlement to the merchant account.

### Authorization object

An approval must bind to an immutable proposal containing:

- obligation or invoice identifier;
- customer or supplier identity and destination details;
- amount and currency;
- requested operation;
- policy version;
- evidence references;
- authorization identifier and expiry.

Changing the amount, destination, operation, policy version, or evidence set
invalidates the authorization and requires a new review.

## Levels

### Level 1 — Evidence-backed receivables desk

**Destination state:** A merchant can load issued invoices and a bounded PayPal
operation fixture, reconcile customer collections, and receive a report with
exact balances and explicit exceptions.

**Included:**

- canonical `RECEIVABLE` invoice and operation schemas;
- source provenance fields;
- deterministic matching by invoice reference, amount, currency, and customer;
- orthogonal obligation, provider, reconciliation, and review states;
- reports for matched, unmatched, partial, refunded, and ambiguous cases;
- no payment execution.

**Adversarial gate:** duplicate invoice, two captures for one invoice, partial
capture, refund after recognition, mismatched currency, pending operation,
ambiguous match, and malformed input.

**Standalone value:** a merchant can understand a PayPal collection period
without authorizing any new payment.

### Level 2 — Source workspace with AI extraction

**Destination state:** The merchant can provide authorized email exports,
attachments, invoices, and contracts; Durin produces candidate facts with
provenance and review requirements.

**Included:**

- source registry and content hashes;
- invoice and contract extraction schema;
- evidence excerpts and source locations;
- prompt-injection-resistant treatment of documents as data;
- human review for low-confidence or contradictory fields;
- Level 1 reconciliation remains the decision layer.

**Adversarial gate:** an invoice containing instructions to ignore policy, a
contract that contradicts an invoice, duplicate attachments, altered source
content, missing excerpts, and extractor output with extra fields.

**Standalone value:** a merchant can inspect and correct extracted obligations
before reconciliation.

### Level 3 — PayPal Sandbox operations

**Destination state:** Durin reads real PayPal Sandbox operations and preserves
provider states, fees, refunds, and recovery states without inventing settlement
claims.

**Included:**

- server-side PayPal credential boundary;
- read adapter for the selected PayPal products;
- provider response normalization that preserves raw status;
- idempotent operation lookup and timeout recovery;
- Level 1 reconciliation against real Sandbox data.

**Adversarial gate:** provider timeout after creation, repeated lookup, pending
order, completed capture, partial refund, duplicate response, API error, and
credentials exposed to the agent.

**Standalone value:** a merchant can reconcile a real Sandbox period and see what
PayPal actually reports.

### Level 4 — Explainable operations reports

**Destination state:** Durin generates daily and period reports from deterministic
results; AI explains the findings but cannot alter them.

**Included:** gross captures, fees, refunds, explicitly scoped net figures,
unmatched invoices and operations, aging, exception prioritization, report
provenance, and generation version.

**Adversarial gate:** narrator substitution, reordered inputs, stale report data,
conflicting PayPal records, missing fees, and a prompt attempting to change a
number.

**Standalone value:** a merchant can understand operational exposure without
opening every invoice and PayPal record manually.

### Level 5 — Authorized payment operations and payable domain

**Destination state:** After `RECEIVABLE` is coherent, Durin adds `PAYABLE` as a
separate domain and supports a PayPal capability appropriate to outgoing
payments, with approval bound to an immutable proposal.

**Included:** independent payable obligations and balances, a capability-specific
PayPal adapter, authorization expiry, idempotent execution and recovery, and no
reuse of receivable formulas where semantics differ.

**Adversarial gate:** changed beneficiary, changed amount after approval,
replayed authorization, duplicate execution, provider timeout, partial result,
revoked policy, and an agent attempting to approve its own proposal.

**Standalone value:** a merchant can operate collection reconciliation and
outgoing payment workflows without confusing the two financial directions.

## Current position

The repository contains a bounded MCP, a pure merchant automation engine, and
agent boundary documentation. Those modules are preparation, not Level 1: the
canonical receivable model, PayPal operation model, and reconciliation engine are
still open.

## Open constraints

| Constraint | State | Revisit trigger |
| --- | --- | --- |
| PayPal capability for outgoing supplier payments | Open, unresolved | Confirm after the receivable adapter is selected. |
| Email provider and consent boundary | Open, unresolved | Choose the first authorized source for Level 2. |
| Settlement/payout evidence | Open, unresolved | Map the exact PayPal response before claiming net settlement. |
| Currency conversion policy | Open, unresolved | Required before multi-currency reconciliation. |

These are open constraints, not completed features or silently discarded
requirements.
