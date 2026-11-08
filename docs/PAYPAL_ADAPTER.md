# PayPal Payouts adapter boundary

Durin prepares a PayPal Payouts v1 request only after a merchant has approved
the exact proposal digest. The current module is offline by design:
`paypal_payouts.py` builds the JSON payload, normalizes provider responses, and
defines recovery instructions. It does not acquire OAuth credentials or make
HTTP requests.

## Invariants

- `proposalDigest` must match both the proposal and the human authorization.
- An expired or reused authorization is rejected before payload construction.
- `sender_batch_id` is derived from the approved digest and must be reused for
  recovery. It is the idempotency identity for the payout batch.
- PayPal batch and item states are preserved as provider data. `SUCCESS` at the
  batch level does not hide `UNCLAIMED`, `RETURNED`, `REFUNDED`, or other item
  exceptions.
- An uncertain outcome requires lookup by batch identity before any recovery
  action. The module never performs a blind duplicate payout.
- `NOT_SUBMITTED` is the only execution state emitted by the offline builder.
- Provider evidence is recorded before interpretation. An unparseable amount,
  unsupported currency, or exact amount mismatch becomes
  `RECONCILIATION_REQUIRED`; it is never discarded and never posted as if it
  matched.

The future Sandbox adapter must keep OAuth credentials outside the MCP agent
and outside the repository. The current test suite uses only synthetic
responses; it does not claim that a payout occurred.

`paypal_client.py` contains the application-side Sandbox client. It is
fail-closed to `api-m.sandbox.paypal.com` or loopback test endpoints, requires
OAuth credentials only at runtime, bounds responses, and exposes create/query
methods without registering them as MCP tools. The caller must still enforce
the approval digest and persist the request identity before invoking it.

The request and recovery rules follow PayPal's official Payouts API reference:

- [Create payout request](https://developer.paypal.com/api/payments.payouts-batch/v1/definitions/create_payout_request/)
- [Show payout batch details](https://developer.paypal.com/api/payments.payouts-batch/v1/payouts-get/)
- [Payout batch header and statuses](https://developer.paypal.com/api/payments.payouts-batch/v1/definitions/payout_batch_header/)
