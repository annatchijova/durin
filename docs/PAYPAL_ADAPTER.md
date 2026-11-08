# PayPal Payouts adapter boundary

Durin prepares a PayPal Payouts v1 request only after a merchant has approved
the exact proposal digest. The current module is offline by design:
`paypal_payouts.py` builds the JSON payload, normalizes provider responses, and
defines recovery instructions. It does not acquire OAuth credentials or make
HTTP requests.

## Invariants

- `proposalDigest` must match both the proposal and the human authorization.
- An expired authorization is rejected before payload construction. A reused
  authorization is rejected at the provider submission boundary; rebuilding a
  request is allowed so recovery can reuse the same idempotency key.
- `sender_batch_id` is derived from the approved digest and must be reused for
  recovery. It is the idempotency identity for the payout batch.
- PayPal batch and item states are preserved as provider data. `SUCCESS` at the
  batch level does not hide `UNCLAIMED`, `RETURNED`, `REFUNDED`, or other item
  exceptions.
- An uncertain outcome requires lookup by batch identity before any recovery
  action. The module never performs a blind duplicate payout.
- Request construction is retry-safe; the authorization is consumed only after
  the PayPal client receives a successful provider response. A confirmed
  authorization cannot be submitted twice in the same process.
- `NOT_SUBMITTED` is the only execution state emitted by the offline builder.
- Provider evidence is recorded before interpretation. An unparseable amount,
  unsupported currency, or exact amount mismatch becomes
  `RECONCILIATION_REQUIRED`; it is never discarded and never posted as if it
  matched.
- A provider completion requires a non-empty unique batch ID, payout item ID,
  transaction ID, and exact provider evidence. Generic `SUCCESS` observations
  without those identities remain unverified.
- The generic operations engine accepts a successful PayPal observation only
  when it carries the attested `providerEvidence` object produced by
  `preserve_provider_evidence()`; declared IDs alone are not sufficient.
- The request builder rejects duplicate invoice IDs, execution-state
  contradictions, observations before approval, and timezone-naive timestamps.

The future Sandbox adapter must keep OAuth credentials outside the MCP agent
and outside the repository. The current test suite uses only synthetic
responses; it does not claim that a payout occurred.

The application deployment should set stable secret material in
`DURIN_AUTHORIZATION_KEY`, `DURIN_PROVIDER_EVIDENCE_KEY`, and
`DURIN_SOURCE_ATTESTATION_KEY`. Without those variables, the local fallback
keys are process-scoped and serialized artifacts cannot be verified after a
process restart.

For any authorized payout execution, set `DURIN_AUTHORIZATION_LEDGER_PATH` to
a shared SQLite file on durable storage. The client refuses an authorized
request when this path is absent. The ledger uses a unique authorization and
proposal key, WAL, busy timeouts, and `BEGIN IMMEDIATE` transitions:

```text
APPROVED -> IN_FLIGHT -> SUBMITTED
```

An uncertain HTTP result remains `IN_FLIGHT`; the recovery path must query the
same provider batch identity before any further action. Call
`finalize_payout_recovery()` only with the response returned by that independent
lookup and the matching `payout_batch_id`. The ledger does not claim
exactly-once delivery across PayPal: it provides durable local state and
idempotent request coordination.

`paypal_client.py` contains the application-side Sandbox client. It is
fail-closed to `api-m.sandbox.paypal.com` or loopback test endpoints, requires
OAuth credentials only at runtime, bounds responses, and exposes create/query
methods without registering them as MCP tools. The caller must still enforce
the approval digest and persist the request identity before invoking it.

Run `python3 scripts/paypal_preflight.py` after loading `.env` to validate the
required Sandbox configuration without network access or transaction submission.

The request and recovery rules follow PayPal's official Payouts API reference:

- [Create payout request](https://developer.paypal.com/api/payments.payouts-batch/v1/definitions/create_payout_request/)
- [Show payout batch details](https://developer.paypal.com/api/payments.payouts-batch/v1/payouts-get/)
- [Payout batch header and statuses](https://developer.paypal.com/api/payments.payouts-batch/v1/definitions/payout_batch_header/)
