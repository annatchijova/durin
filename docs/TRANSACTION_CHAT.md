# Transaction history chat — the competitive advantage

## The pain this solves

A merchant with hundreds of PayPal transactions gets a message from a
supplier or client: "you still owe me for that payment from six months
ago." Today that means scrolling PayPal's own history by hand, hoping to
recognize the right row by amount and date.

Durin answers this in natural language: *"did we pay Acme around $450 a few
months ago?"* — searched against the merchant's real PayPal transaction
history, not a guess, not a local cache that only knows what Durin itself
processed.

## Why this is not "the LLM reads your transactions and tells you"

That framing would put a model in the decision path, which is the one
invariant this whole project refuses to cross (see `docs/AGENT.md`,
`docs/CONSTRUCTION_LEVELS.md`'s authority-separation section). The chat
keeps the model on both ends of a deterministic core, never inside it:

```text
merchant question
        -> openai_chat_client.interpret_query()      (model: proposes hints, not facts)
        -> paypal_transaction_search.chunk_date_range()   (deterministic)
        -> paypal_client.search_transactions()            (real PayPal API, repeated per chunk)
        -> paypal_transaction_search.filter_transactions() (deterministic match + rank)
        -> openai_chat_client.narrate_results()       (model: explains only what was found)
```

- `interpret_query` turns free text into `{monthsBack, counterpartyHint,
  amountHint, keywords}`. This is a guess about what to search for. It is
  never treated as a fact and never used to construct an answer directly.
- The actual search runs against PayPal's real Transaction Search API
  (`GET /v1/reporting/transactions`), chunked into PayPal's own ~31-day
  window limit (`chunk_date_range`, bounded to 24 months / 24 chunks so a
  malformed hint can't trigger an unbounded number of real API calls).
- `filter_transactions` is pure Python: amount match within a 2% tolerance,
  counterparty substring match, keyword match against subject/note/invoice
  id. A hint that matches nothing returns an empty list — never a fabricated
  best guess standing in for "not found."
- `narrate_results` receives only the transactions `filter_transactions`
  already matched, as the complete and only truth it is allowed to use, and
  is instructed to say plainly when nothing was found rather than invent a
  transaction outside that list.
- The frontend (`ChatWidget.tsx`) renders the narrated answer *and* the
  cited transactions as separate chips (id, amount, counterparty), so the
  prose stays checkable against real data instead of being taken on faith —
  the same evidence-first posture as the rest of the product.

## What's real vs. what's pending

The full pipeline is live-tested through the browser: a real OpenAI call
interprets the question, a real PayPal Sandbox call attempt is made, and
the response reaches the chat UI end to end with a clean error when PayPal
rejects it. The one open item is operational, not architectural: this
Sandbox app did not have PayPal's "Transaction Search" feature enabled by
default (it was unchecked despite being listed), and the scope had not
finished propagating as of the last live check. Once it does, no code
changes -- the same call already in place returns real transaction data.

## Demo note

For a recorded demo on a deployed environment (e.g. Vercel) with no live
PayPal/OpenAI calls desired, `api_server.py`'s `/api/chat` is the only seam
that needs a pre-recorded fixture response; the frontend component already
renders whatever that endpoint returns without caring whether it came from
a live call or a fixture. The live demo should keep calling the real APIs,
per the plan to show real calls at that moment.
