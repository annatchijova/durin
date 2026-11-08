#!/usr/bin/env bash
set -euo pipefail

# Run the local MCP with a minimal filesystem and no network access.
# PayPal integration is not part of this process yet.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BWRAP="/usr/bin/bwrap"

if [[ ! -x "$BWRAP" || "$(realpath "$BWRAP")" != "/usr/bin/bwrap" ]]; then
  echo "bwrap is required; refusing to launch without a sandbox" >&2
  exit 78
fi

if [[ ! -f "$PROJECT_DIR/mcp_server.py" || ! -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  echo "mcp_server.py or .venv/bin/python is missing" >&2
  echo "Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 78
fi

INPUT_DIR="${DURIN_INPUT_DIR:-$PROJECT_DIR/sandbox-input}"
INVOICE_PATH="${DURIN_INVOICES_PATH:-}"
ARGS=(
  --clearenv
  --ro-bind /usr /usr
  --ro-bind /bin /bin
  --ro-bind /lib /lib
  --ro-bind /lib64 /lib64
  --ro-bind /etc /etc
  --dir /app
  --ro-bind "$PROJECT_DIR/mcp_server.py" /app/mcp_server.py
  --ro-bind "$PROJECT_DIR/.venv" /app/.venv
  --chmod 0555 /app
  --tmpfs /home
  --tmpfs /tmp
  --proc /proc
  --dev /dev
  --dir /tmp/home
  --setenv PATH /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
  --setenv HOME /tmp/home
  --setenv VIRTUAL_ENV /app/.venv
  --setenv PYTHONDONTWRITEBYTECODE 1
  --setenv PYTHONUNBUFFERED 1
  --chdir /app
  --unshare-user
  --unshare-pid
  --unshare-ipc
  --unshare-uts
  --unshare-cgroup
  --unshare-net
  --disable-userns
  --assert-userns-disabled
  --die-with-parent
  --new-session
  --cap-drop ALL
  --uid 65534
  --gid 65534
)

if [[ -n "$DURIN_POLICY_JSON" ]]; then
  ARGS+=(--setenv DURIN_POLICY_JSON "$DURIN_POLICY_JSON")
fi

if [[ -n "$INVOICE_PATH" ]]; then
  INPUT_DIR="$(realpath -e -- "$INPUT_DIR")"
  INVOICE_PATH="$(realpath -e -- "$INVOICE_PATH")"
  case "$INVOICE_PATH" in
    "$INPUT_DIR"/*) ;;
    *) echo "DURIN_INVOICES_PATH must be inside DURIN_INPUT_DIR" >&2; exit 78 ;;
  esac
  ARGS+=(
    --ro-bind "$INPUT_DIR" /sandbox-input
    --setenv DURIN_INVOICES_PATH "/sandbox-input/${INVOICE_PATH#"$INPUT_DIR"/}"
  )
fi

ulimit -c 0
ulimit -f 10240
ulimit -n 256
ulimit -t 120

exec "$BWRAP" "${ARGS[@]}" /app/.venv/bin/python /app/mcp_server.py
