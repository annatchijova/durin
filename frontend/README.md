# Durin frontend

Shows what the AI interpreted, what the deterministic engine verified, and
what the merchant authorized, as one journey per invoice: evidence received,
data extracted (with the literal excerpt behind every field), contradictions
across sources, proposal prepared, human approval, PayPal result.

This app never talks to OpenAI or PayPal, and never sees a credential. It
only talks to `api_server.py` (FastAPI, repo root), which is the sole holder
of those secrets. Mutating actions (propose, approve, submit, refresh) go
through this app's own Route Handlers under `src/app/api/*`, which proxy to
the Python API server-side — the browser never calls the Python API's
host/port directly.

## Run locally

```shell
# 1. Start the Python API (repo root, with .env loaded)
cd ..
set -a; . ./.env; set +a
python3 -m uvicorn api_server:app --host 127.0.0.1 --port 8010

# 2. Start the frontend
cd frontend
npm install
DURIN_API_URL=http://127.0.0.1:8010 npm run dev
```

Then open http://127.0.0.1:3000, and run extraction against a source
directory from the dashboard.

## Recorded demo on a static host

With `DURIN_DEMO_SNAPSHOT=1` (set on Vercel for production and preview) the
app serves the three cases under `src/lib/demo-cases/` instead of calling
`api_server.py`. They are unedited JSON files written by the API during real
local runs on 2026-11-09 (OpenAI extraction, deterministic engine, PayPal
sandbox payout); only the local scratch directory in source paths was
replaced by `demo-sources/`. A banner says so on every page and every
mutating action is refused with a message. Leave the variable unset locally
so a backend that is merely down still shows the "backend not reachable"
notice. `NEXT_PUBLIC_DURIN_SLIDES_URL` enables the slides link on the landing.

## Export

The case page and the dashboard export a CSV (`src/lib/export.ts`: one line
per engine row, or one per case, with the stored fields only -- nothing is
re-computed) and a PDF through the browser's print dialog over the print
stylesheet in `globals.css`, the same approach as `/vertice`.

## Operational layer

The journey is the evidence trail; around it sits a thin operational layer
that answers "what needs attention, and what is the next authorized step?"
without becoming a second source of truth.

- `src/lib/decision.ts` is the only place those answers are computed. It is
  a pure projection of the case `api_server.py` stored: it selects and counts
  existing fields and never adds amounts (totals arrive from the engine as
  strings).
- **Decision summary** (`DecisionSummary.tsx`): stage, sealed total,
  suppliers, included/excluded invoices, contradictions, proposal digest,
  PayPal state, and exactly one next step. It holds no mutating control —
  the next step is a link to the journey step where the real control sits
  beside its evidence, so approval and submission keep one entry point each.
  Sticky side column from `lg` up; above the journey on small screens.
- **Dashboard views** (`DashboardView.tsx`): every tile count is
  `cases.filter(VIEW_PREDICATE[view]).length` and selecting the tile applies
  the same predicate, so a metric cannot show a number its filter does not
  reproduce. The selected view is kept in `?view=`. Views overlap on purpose
  (a reconciled case can still carry excluded invoices).
- **Activity record** (`ActivityLog.tsx`): collapsed by default, rendered
  from the case's structured records in lifecycle order, raw record behind a
  second disclosure. A timestamp is shown only when the record has one.
- **Actor ownership** (`ActorChip.tsx`): each step is tagged with who owns it
  (source, AI, engine, you, PayPal).

### Known limitations

- The backend does not timestamp individual submit or refresh attempts, so
  the activity record shows "time not recorded" for a failed submission and
  for reconciliation. It is a projection of current case state, not an
  append-only event ledger; a real one needs `api_server.py` to record events.
- The "contradictions" count is the cross-source contradictions plus the rows
  the engine excluded for a supplier-identity or invoice-fact conflict. Two
  rows that conflict with each other therefore count as two.
- Case-card totals are the engine's ready-to-pay totals by currency, not the
  sealed proposal total (the list endpoint does not carry the proposal).
- Date filtering uses the browser clock against the case's `createdAt`.
- Accessibility was checked with axe-core (WCAG 2 A/AA rules) on the landing,
  dashboard, and case pages at desktop and phone widths, plus a scripted
  keyboard check of the chat. No screen-reader pass has been done.

## Design

Palette and component language adapted from two sibling projects'
design systems (`/vertice`'s token set, `/velo`'s component patterns),
re-themed for Durin: a neutral "ink" scale carries the page, a single PayPal-
blue accent is reserved for the primary action, and four semantic states
(`ready` / `exception` / `review` / `pending` — see `src/lib/classify.ts`)
replace Durin's many raw reason codes with one consistent visual language,
so an exception always reads as an exception regardless of which check
produced it.

## i18n

English is the default and dominant language; Spanish is a toggle
(`src/lib/i18n.tsx`, same pattern as `/velo`). All UI copy goes through
`useI18n()`'s `t()` — never a hardcoded string in a component.
