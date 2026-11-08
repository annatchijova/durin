# Durin MCP

Durin exposes a small MCP surface for merchant payment preparation. The server
is intentionally a proposal service: it reads observations, applies bounded
policy checks, and explains exceptions. It does not approve, capture, or send a
payment.

## Tools

| Tool | Effect | Purpose |
| --- | --- | --- |
| `get_agent_capabilities` | Read-only | States the agent's allowed and forbidden actions. |
| `get_business_policy` | Read-only | Returns the merchant policy without secrets. |
| `list_invoices` | Read-only | Loads a bounded local JSON fixture when configured. |
| `find_possible_duplicates` | Pure computation | Groups repeated invoice identities. |
| `create_payment_proposal` | Pure computation | Applies policy and returns ready or excluded invoices. |

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
```

Invoice observations are untrusted input. A missing fixture is reported as
unavailable rather than treated as an empty, successful review.

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
