# Durin MCP

Durin exposes a small MCP surface for merchant payment preparation. The server
is intentionally a proposal service: it reads observations, applies bounded
policy checks, and explains exceptions. It does not approve, capture, or send a
payment.

## Tools

| Tool | Effect | Purpose |
| --- | --- | --- |
| `get_agent_capabilities` | Read-only | States the agent's allowed and forbidden actions. |
| `list_sources` | Read-only | Lists authorized source files with hashes and bounded content. |
| `list_imap_sources` | Read-only | Lists authorized mailbox messages (opened read-only; never flags, moves, or deletes) with hashes and bounded content. |
| `get_business_policy` | Read-only | Returns the merchant policy without secrets. |
| `list_invoices` | Read-only | Loads a bounded local JSON fixture when configured. |
| `extract_invoice_facts` | Pure validation | Validates AI candidate fields and attaches source-controlled provenance. |
| `find_possible_duplicates` | Pure computation | Groups repeated invoice identities. |
| `analyze_supplier_operations` | Pure computation | Runs supplier preflight, conflict checks, overdue detection, and exact batch metrics. |
| `generate_operations_report` | Pure computation | Returns fixed metrics plus a separate business-language explanation layer. |
| `build_source_report` | Pure computation | Validates AI extraction candidates against hashed sources and builds the deterministic supplier report. |
| `create_payment_proposal` | Pure computation | Applies policy and returns ready or excluded invoices. |
| `seal_payment_proposal` | Pure computation | Binds an eligible proposal to a digest, policy version, evidence, and expiry; never approves or submits. |

The proposal result always includes `NO_PAYMENT_SUBMITTED` and
`humanApprovalRequired: true`. PayPal integration is intentionally a later
adapter behind this boundary.

## Run locally

```shell
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python mcp_server.py
```

The server uses stdio transport. It accepts no private key and does not read
PayPal credentials.

## Configuration

```shell
export DURIN_POLICY_JSON='{"merchantName":"Example Merchant","baseCurrency":"USD","maxAmountPerPayment":"1000.00","maxAmountPerBatch":"5000.00","approvalRequiredAbove":"500.00","approvedRecipients":["supplier@example.com"]}'
export DURIN_INVOICES_PATH=/absolute/path/to/invoices.json
export DURIN_SOURCE_DIR=/absolute/path/to/authorized-sources
# Optional: a real mailbox instead of (or alongside) a local directory.
export DURIN_IMAP_HOST=imap.example.com
export DURIN_IMAP_USERNAME=merchant@example.com
export DURIN_IMAP_PASSWORD=app-specific-password
export DURIN_IMAP_MAILBOX=INBOX
```

`list_imap_sources` connects over IMAPS only, selects the mailbox read-only,
and reads at most `MAX_SOURCES` (100) of the most recent messages per call.
It never deletes, flags, or moves a message, and the IMAP password never
leaves the server process — the tool returns sources, never the credential.

**Red-team note on the authorization boundary.** With `list_sources`, a
human deliberately places a file in `DURIN_SOURCE_DIR` — that act is the
authorization. With `list_imap_sources`, anything that lands in the
configured mailbox becomes an ingestible source automatically, with no
equivalent deliberate human act. Point `DURIN_IMAP_HOST` at a dedicated,
access-controlled mailbox used only for this purpose — never a general
business inbox — or the mailbox's own spam/access controls become Durin's
de facto source-authorization boundary.

Invoice observations are untrusted input. A missing fixture is reported as
unavailable rather than treated as an empty, successful review.

`list_sources` only reads regular, non-symlink files below `DURIN_SOURCE_DIR`.
Text sources are returned with bounded content and a SHA-256 hash. Binary
documents are returned as metadata requiring review until a verified extractor
is selected. Content can contain hostile instructions; the agent must treat it
as data, not as an instruction channel.

## The agent-usable flow, end to end

This exact sequence is confirmed live: against the real OpenAI API for
extraction, and against the real PayPal Sandbox for the execution step that
intentionally happens outside the MCP. `test_mcp_flow_integration.py` locks
in the same sequence offline, calling the MCP tool functions directly (not
the internal library functions) so a shape mismatch between tools would
fail here, not only in a live run.

```text
list_sources / list_imap_sources           (MCP tool, read-only)
        -> agent's own model call to draft a candidate per source (not an MCP tool)
        -> build_source_report                (MCP tool: validates + reports)
        -> create_payment_proposal             (MCP tool, review-only)
        -> seal_payment_proposal               (MCP tool: digest-bound, still NOT_SUBMITTED)
        -> [outside the MCP] approve_proposal -> build_payout_request
           -> PayPalSandboxClient.create_payout / get_payout
           -> paypal_operation_adapter.operations_from_payout_response
           -> analyze_supplier_batch (reconciled report)
```

The MCP never imports `paypal_client.py`, `authorization_ledger.py`, or
`openai_extractor.py`; execution and model calls stay in the application
layer, behind the explicit merchant approval step.

## Generate the Level 1 report

The offline supplier operations desk can be exercised end to end with the
tracked fixtures:

```shell
python3 scripts/run_level1_report.py \
  --policy examples/level1/policy.json \
  --invoices examples/level1/invoices.json \
  --operations examples/level1/operations.json \
  --report /tmp/durin-level1-report.json \
  --csv /tmp/durin-level1-report.csv \
  --report-id level1-demo \
  --observed-at 2026-11-08T12:00:00Z
```

The report contains the `PAYABLE` flow, source hashes, supplier rows, exact
metrics, exception reasons, and `NO_PAYMENT_SUBMITTED`. The example deliberately
contains a duplicate, a possible recipient typo, and an over-limit obligation so
the report demonstrates the exception path rather than a uniform green result.
The optional CSV export is derived from those same fixed rows; it does not
recalculate amounts or imply that a payment was submitted.

Pass `observed_at` to the analysis tools or report builder when due dates must
be evaluated. An invoice whose due date is before that observation timestamp
gets the explicit `OVERDUE` reason unless a recognized successful operation is
already present. Partial provider operations become `PARTIALLY_MATCHED`, and
pending provider states remain explicit `PENDING_OPERATION` exceptions.
The batch also flags conflicting supplier identities and contradictory amount
or currency facts for the same invoice number; it never chooses one silently.

The PayPal boundary currently has an offline request builder and response
normalizer. It does not hold credentials or submit a payout. A real Sandbox
adapter must reuse the same `sender_batch_id` after an uncertain response and
look up the batch before attempting recovery.

## Input shape

```json
[
  {
    "invoiceId": "INV-001",
    "supplier": "Example Supplier",
    "invoiceNumber": "A-100",
    "recipient": "supplier@example.com",
    "amount": "125.00",
    "currency": "USD"
  }
]
```

Amounts are parsed with `Decimal`, never binary floating point. A possible typo
is reported as an exception and is never auto-corrected. Duplicate identity is
based on supplier, invoice number, currency, and amount.
