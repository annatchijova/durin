# Red-Team Variant Analysis — 2026-11-08

## Scope and method

This is a second, read-only adversarial pass over commit `a481c5f`. It follows
the variant-analysis method: each initial finding was abstracted into an
invariant, every sibling sink or entry point was searched, and each candidate
variant was independently exercised where possible.

The audit covered `source_ingestion`, `source_workflow`, `supplier_operations`,
`automation`, `authorization`, `mcp_server`, `paypal_payouts`,
`paypal_reconciliation`, and `paypal_client`.

Threat model: an attacker or untrusted upstream integration can control source
objects, extraction candidates, operation observations, provider responses, or
serialized objects passed into application boundaries. Environment-controlled
vectors are marked conditional. The audit did not access the network, use
credentials, call PayPal, deploy anything, or send a transaction.

Baseline: `python3 -m unittest discover -s . -p 'test_*.py'` — 46 tests passed,
0 failed, 0 skipped. The reproducible offline probes are in
`scripts/redteam_variant_round.py`.

## Finding status vocabulary

- **CODE FACT**: visible in the live source.
- **CONFIRMED BY INDUCTION**: a predicted consequence was reproduced by an
  offline probe or test.
- **PLAUSIBLE HYPOTHESIS**: the code supports the concern, but the required
  product contract or deployment condition is not established.
- **FALSIFIED**: the predicted consequence did not occur under the tested
  conditions.

## Variant matrix

| ID | Severity | Status | Invariant family | Result |
| --- | --- | --- | --- | --- |
| VA-01 | High | Duplicate of RT-01 | Source provenance | Caller-controlled source identity and hash remain accepted. |
| VA-02 | High | Confirmed | Evidence binding | A valid excerpt need not contain the extracted field value. |
| VA-03 | Medium | Confirmed | Source identity uniqueness | Repeated `sourceId` creates repeated invoice identity. |
| VA-04 | High | Expanded duplicate of RT-08 | Review authority | `requiresReview` is metadata, not a deterministic exclusion barrier. |
| VA-05 | Medium | Confirmed | Cardinality limits | The workflow sink bypasses the 100-source ingestion limit. |
| VA-06 | High | Confirmed | Operation identity | Generic reconciliation can match another supplier's operation. |
| VA-07 | Medium | Confirmed | Provider state semantics | Failed or unknown operation states can lack explicit exception reasons. |
| VA-08 | High conditional | Confirmed | Provider provenance | Caller-supplied `SUCCESS` operations reach reports without provider evidence. |
| VA-09 | Medium conditional | Confirmed | Temporal authority | A payout request can be built with an observation before approval. |
| VA-10 | Medium | Confirmed | Execution state | `proposal.execution` is not enforced by the payout builder. |
| VA-11 | Medium | Expanded duplicate of RT-07 | Provider identity/cardinality | Successful provider responses can lack or duplicate IDs and still complete. |
| VA-12 | Medium | Narrowed | Numeric boundary | Positive `Infinity`, `NaN`, and signaling NaN escape the provider parser. |
| VA-13 | Medium | Confirmed | Configuration finiteness | `timeout_seconds=NaN` passes configuration validation. |
| VA-14 | High conditional | Expanded duplicate of RT-06 | URL authority | Userinfo can make the allowlisted text differ from the real host. |
| VA-15 | Medium | Expanded duplicate of RT-10 | Idempotency identity | PayPal header and payload batch IDs are independently supplied. |
| VA-16 | Plausible | Code fact only | Currency contract | Invoice currency is not explicitly tied to policy base currency. |

## Detailed findings

### VA-02 — Excerpt support does not bind the extracted value

**Observation:** `validate_invoice_extraction()` checks only whether each
evidence excerpt is a substring of source content. It does not check whether
the candidate field value appears in that excerpt or is otherwise derived from
the source.

**Induction:** A source containing `Amount: 100.00 USD` can be paired with a
candidate amount of `999.99` and a generic excerpt such as `Amount:`. The
candidate is marked supported when the excerpt occurs in the source.

**Impact:** A genuine source can carry a fabricated amount, recipient, or date
into the deterministic engine. This is independent of the source-spoofing
finding: it survives even when the source was genuinely ingested.

### VA-03 — Duplicate source identity produces duplicate obligations

**Observation:** `build_report_from_extractions()` does not reject repeated
`sourceId` values or compare repeated source hashes, paths, or content.

**Induction:** Two source objects with `sourceId=src-1` produce two extracted
rows with the same generated `invoiceId=source-src-1`. The report proceeds and
the duplicate engine becomes the first place that notices a collision.

**Impact:** Duplicate report rows, ambiguous evidence references, repeated
`sender_item_id` values, and unstable authorization/idempotency semantics.

### VA-04 — Review labels have no downstream authority

**Observation:** `source_workflow` records `requiresReview`, but
`supplier_operations` and `automation.prepare_proposal()` do not enforce it.

**Induction:** A direct invoice with `requiresReview=true` is accepted into a
`READY_FOR_REVIEW` proposal. Unsupported evidence can also produce an empty
reason list, while `requiresReviewCount` counts string `"false"` as truthy.

**Impact:** The system can present a review-required item as proposal-eligible.
The label is descriptive, not a gate.

### VA-05 — Source cardinality is not preserved across entry points

**Observation:** `list_sources()` enforces `MAX_SOURCES=100`, but
`build_report_from_extractions()` accepts an unbounded `sources` list.

**Induction:** A caller can bypass ingestion and submit more than 100 source
objects directly to the workflow.

**Impact:** Availability and cost pressure, plus inconsistent security posture
between MCP paths.

### VA-06 — Generic operation matching uses insufficient identity

**Observation:** `supplier_operations._operation_for()` accepts an operation
when `invoiceId` or `invoiceNumber` matches. It does not require supplier,
recipient, provider item, transaction, and batch identity to agree.

**Induction:** An operation for another recipient with the same invoice number
can be attached to the invoice and influence the report.

**Impact:** Cross-supplier contamination of operational reports and metrics.

### VA-07 — Failed and unknown states do not consistently create exceptions

**Observation:** The operation engine preserves arbitrary statuses and can
recognize a failed partial amount without an explicit failed-operation reason.

**Induction:** `FAILED` with a partial amount becomes `PARTIALLY_MATCHED`; an
exact `FAILED` operation can yield `FAILED` with no reason; an arbitrary status
can remain a row state without a reason.

**Impact:** Exception-first reporting is weakened. This is not the same as a
false `SUCCESS`, but it can hide why a human must investigate.

### VA-08 — Operations can be asserted without provider provenance

**Observation:** The source workflow accepts an `operations` array without a
PayPal response envelope, provider request ID, transaction ID, or preserved
evidence record.

**Induction:** A caller-supplied operation with `status=SUCCESS` reaches the
report as a successful operation.

**Condition:** This becomes an external security issue only if an untrusted
caller can populate operations. Otherwise it remains a trust-boundary design
gap at the application boundary.

### VA-09 — Approval and observation time are not one state machine

**Observation:** `build_payout_request()` checks that the observation is not
after expiry, but does not require `approvedAt <= observed_at`.

**Induction:** A request with approval at 12:05 and observation at 12:00 is
accepted. A naive timestamp instead raises an uncaught `TypeError` when mixed
with an aware timestamp.

**Condition:** The bypass requires control over the observation timestamp or a
non-centralized clock boundary.

### VA-10 — Execution state is not enforced

**Observation:** The payout builder requires `proposal.status=PENDING_APPROVAL`
but does not require `proposal.execution=NO_PAYMENT_SUBMITTED`.

**Induction:** A digest over a proposal whose execution field is `EXECUTED` can
still be approved and passed to the builder, which emits `NOT_SUBMITTED`.

**Impact:** State labels can contradict the action boundary and undermine replay
and recovery reasoning.

### VA-11 — Provider success lacks identity and cardinality checks

**Observation:** `normalize_payout_response()` derives completion from batch and
listed item statuses, without requiring a batch ID, payout item IDs,
transaction IDs, uniqueness, or expected item cardinality.

**Induction:** A `SUCCESS` batch with one `SUCCESS` item and no IDs yields
`PROVIDER_COMPLETED`. Empty items are correctly downgraded to
`REVIEW_ITEM_STATES`; that negative control is important.

### VA-12 — Numeric special values are not uniformly bounded

**Observation:** `_amount()` catches `InvalidOperation` but does not reject all
non-finite values before comparisons/quantization.

**Induction:** `Infinity` raises an uncaught `TypeError`; `NaN` and signaling
NaN escape as decimal exceptions. `-Infinity` is correctly converted to a
controlled reconciliation error, so the broad claim “all specials escape” is
falsified and narrowed.

### VA-13 — NaN timeout passes validation

**Observation:** `timeout_seconds` is checked only with range comparisons.

**Induction:** `float('nan')` passes because both comparisons are false.
`0`, `61`, and positive infinity remain rejected; this is a narrow variant.

### VA-16 — Currency policy is underspecified

**Observation:** `prepare_proposal()` can accept an invoice currency different
from `policy.baseCurrency`.

**Interpretation:** This is a code fact, not yet a confirmed defect. It is valid
if Durin intentionally supports multi-currency proposals and invalid if the
policy promises one base currency. The product contract must decide.

## Negative controls and discarded vectors

The following did not reproduce under the current code:

- Symlink ingestion: rejected by `list_sources()`.
- Mainnet PayPal host and non-HTTP schemes: rejected.
- Userinfo URL without the crafted port form: rejected.
- `-Infinity` provider amount: controlled reconciliation error.
- Timeout `0`, `61`, and positive infinity: rejected.
- Empty provider items on a successful batch: downgraded to review.
- Reusing an old proposal digest after changing the amount: rejected.
- Unauthorized extraction field such as `approve_payment`: rejected.
- Real PayPal transaction, network call, and redirect: not executed.

## Dedupe and fix coverage

No fixes were applied in this pass. The following first-round findings remain
open and were independently re-confirmed or expanded: RT-01, RT-06, RT-07,
RT-08, RT-09, and RT-10. New families are VA-02, VA-03, VA-05, VA-06, VA-07,
VA-08, VA-09, VA-10, VA-12, VA-13, and the contract question VA-16.

The key coverage conclusion is compositional: fixing one source entry point,
one status parser, or one PayPal response field will not close the family unless
all sibling sinks preserve the same invariant.

## Decision

**Do not declare the PayPal boundary production-ready or authorize fixes as
complete.** The audit found enough independent variants to require a second
design pass over provenance authority, review gating, operation identity,
provider evidence, temporal normalization, and configuration validation.

This document and `scripts/redteam_variant_round.py` are audit artifacts only;
they do not send payments and do not alter production logic.
