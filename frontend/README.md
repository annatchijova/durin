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
