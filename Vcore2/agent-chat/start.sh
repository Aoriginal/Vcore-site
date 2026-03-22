#!/usr/bin/env bash
# ── VCore Agent Chat — Startup Script ────────────────────────────────────────
# Usage: ./start.sh [--port 8765] [--host 0.0.0.0] [--export-path /path/to/dir]
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT=${PORT:-8765}
HOST=${HOST:-127.0.0.1}
EXPORT_PATH=${VCORE_EXPORT_PATH:-"$SCRIPT_DIR/ConversationHistory"}

# Parse args
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --port)         PORT="$2";        shift ;;
    --host)         HOST="$2";        shift ;;
    --export-path)  EXPORT_PATH="$2"; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# Create dirs
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$EXPORT_PATH"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  VCore Agent Chat Platform"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  URL:         http://${HOST}:${PORT}"
echo "  Export path: ${EXPORT_PATH}"
echo "  Database:    ${SCRIPT_DIR}/data/vcore_chat.db"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check for Python venv
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
  echo "→ Creating Python virtual environment…"
  python3 -m venv "$SCRIPT_DIR/.venv"
fi

# Activate venv
source "$SCRIPT_DIR/.venv/bin/activate"

# Install/update dependencies
echo "→ Installing dependencies…"
pip install -q -r requirements.txt

echo "→ Starting server on http://${HOST}:${PORT} …"
echo ""

export VCORE_EXPORT_PATH="$EXPORT_PATH"
exec uvicorn main:app \
  --host "$HOST" \
  --port "$PORT" \
  --reload \
  --log-level info
