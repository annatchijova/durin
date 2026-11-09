# AI extraction boundary

This is the production AI extraction provider referenced as an open constraint
in `docs/CONSTRUCTION_LEVELS.md`. It fills the gap between `list_sources` and
`source_workflow.build_report_from_extractions`: something has to turn source
text into candidate invoice fields before validation can run.

## Why the model stays out of the decision path

`openai_extractor.py` calls OpenAI with a strict JSON schema and returns a
draft `candidate`. That draft is not trusted:

- `source_ingestion.validate_invoice_extraction` re-checks every field against
  the literal source content. A field is `SUPPORTED` only when the model's
  cited `evidence` excerpt is an exact substring of the source and the
  extracted value is a substring of that excerpt. An unsupported field is
  marked `requiresReview`, never silently accepted.
- `draft_ledger.py` records the candidate as `DRAFT` before it is used for
  anything. A draft can move to `REVIEWED` or `REJECTED`, but once it leaves
  `DRAFT` it is never silently re-extracted and overwritten; a merchant's
  review decision is final evidence, not a cache entry.
- `contradiction_detection.py` compares the validated `recipient`, `dueDate`,
  and `concept` fields across multiple sources describing the same obligation
  (`supplier` + `invoiceNumber`). It deliberately does not re-check `amount`
  or `currency`: `supplier_operations.analyze_supplier_batch` already raises
  `CONFLICTING_INVOICE_FACTS` for those, and policy violations
  (`RECIPIENT_NOT_APPROVED`, `CURRENCY_NOT_SUPPORTED`,
  `EXCEEDS_PER_PAYMENT_LIMIT`) already surface as row-level reasons from
  `automation.py`/`supplier_operations.py`. This module adds the one check
  the existing engine has no field for: a different recipient, due date, or
  concept cited by two documents for the same obligation, kept with both
  sources' evidence excerpts so a human — not the model — resolves it.
- Swapping the model (a different OpenAI model, or a different provider
  behind the same `extract_candidate` shape) can only change which draft is
  proposed. It cannot change whether a field is accepted — that check runs
  against the source text, not against the model's claim.

## Pipeline

```text
list_sources(DURIN_SOURCE_DIR)
        -> openai_extractor.extract_candidate() per eligible source  (DRAFT)
        -> draft_ledger.record_draft()                                (DRAFT, durable)
        -> source_ingestion.validate_invoice_extraction()              (grounded or requiresReview)
        -> contradiction_detection.detect_source_contradictions()      (recipient/dueDate/concept cross-source)
        -> supplier_report.build_supplier_report()                    (deterministic report)
```

Run it with:

```shell
set -a
. ./.env
set +a
python3 scripts/run_ai_extraction_pipeline.py
```

Required environment: `OPENAI_API_KEY`, `DURIN_SOURCE_DIR`,
`DURIN_DRAFT_LEDGER_PATH`, `DURIN_POLICY_JSON`. `DURIN_OPERATIONS_PATH` is
optional; without it the report has no provider operations to reconcile
against yet.

## Limits of this pass

- `openai_extractor.py` only extracts the `ALLOWED_INVOICE_FIELDS` from
  `source_ingestion.py` (supplier, invoiceNumber, recipient, amount,
  currency, dueDate, concept). It does not yet extract contract terms as a
  separate schema, so a contract document's payment terms are not yet
  cross-checked against an invoice's due date beyond what both sides state as
  an `INVOICE`-kind source.
- A draft never becomes a payment proposal on its own. `automation.py` and
  `authorization.py` still require a separate, explicit step before any
  PayPal action.
- This script has no retry/backoff policy for OpenAI rate limits; a failed
  source is reported in `extractionErrors` and skipped, not silently dropped.
