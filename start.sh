#!/usr/bin/env bash
# ABC AI Support Platform - one-command start.
#
#   ./start.sh            install what's needed (first run only) and start the app
#   ./start.sh --reset    same, but wipe the database back to fresh demo data
#
# Everything runs as ONE program on ONE port (8000): the API, the API docs and
# the website. Works in GitHub Codespaces, GitHub Actions and any Linux/macOS
# machine with Python 3.10+ and Node.js 18+.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
PORT="${PORT:-8000}"
say() { printf '\033[1;34m[setup]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

# --- 1. Check tools -----------------------------------------------------------
PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || fail "Python 3.10+ is required but was not found."
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || fail "Python 3.10+ is required (found $("$PY" --version 2>&1))."
command -v node >/dev/null || fail "Node.js 18+ is required but was not found."
node -e 'process.exit(parseInt(process.versions.node) >= 18 ? 0 : 1)' \
  || fail "Node.js 18+ is required (found $(node --version))."
command -v npm >/dev/null || fail "npm is required but was not found."
say "Using $("$PY" --version 2>&1) and Node $(node --version)"

# --- 2. Backend dependencies (re-installed only when requirements.txt changes) --
VENV="$ROOT/.venv"
REQ="$ROOT/backend/requirements.txt"
STAMP="$VENV/.requirements.sha"
REQ_SHA="$("$PY" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$REQ")"
if [ ! -x "$VENV/bin/python" ]; then
  say "Creating Python environment (.venv)..."
  "$PY" -m venv "$VENV"
fi
if [ "$(cat "$STAMP" 2>/dev/null || true)" != "$REQ_SHA" ]; then
  say "Installing backend packages (first run takes about a minute)..."
  "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check --upgrade pip
  "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$REQ"
  echo "$REQ_SHA" > "$STAMP"
else
  say "Backend packages already installed"
fi

# --- 3. Website (built into frontend/dist and served by the backend) ----------
LOCK_SHA="$("$PY" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$ROOT/frontend/package-lock.json")"
if [ ! -d "$ROOT/frontend/node_modules" ] || [ "$(cat "$ROOT/frontend/node_modules/.lock.sha" 2>/dev/null || true)" != "$LOCK_SHA" ]; then
  say "Installing website packages..."
  (cd "$ROOT/frontend" && npm ci --no-audit --no-fund --loglevel=error)
  echo "$LOCK_SHA" > "$ROOT/frontend/node_modules/.lock.sha"
fi
say "Building the website..."
(cd "$ROOT/frontend" && npm run build --silent >/dev/null)
[ -f "$ROOT/frontend/dist/index.html" ] || fail "Website build did not produce frontend/dist/index.html"

# --- 4. Database + secret (kept in backend/data/, never committed) -------------
DATA="$ROOT/backend/data"
mkdir -p "$DATA"
if [ "${1:-}" = "--reset" ]; then
  say "Resetting database to fresh demo data..."
  rm -f "$DATA/abc_support.db"
fi
export DATABASE_URL="${DATABASE_URL:-sqlite:///$DATA/abc_support.db}"
if [ -z "${JWT_SECRET:-}" ]; then
  [ -s "$DATA/jwt_secret" ] || "$PY" -c 'import secrets; print(secrets.token_urlsafe(48))' > "$DATA/jwt_secret"
  JWT_SECRET="$(cat "$DATA/jwt_secret")"
  export JWT_SECRET
fi
export APP_ENV="${APP_ENV:-demo}"
export STATIC_DIR="$ROOT/frontend/dist"

# --- 5. Start ------------------------------------------------------------------
if [ -n "${CODESPACE_NAME:-}" ]; then
  URL="https://${CODESPACE_NAME}-${PORT}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
else
  URL="http://localhost:${PORT}"
fi

# Print the address once the app is really answering.
(
  for _ in $(seq 1 180); do
    if "$VENV/bin/python" -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:${PORT}/api/health', timeout=2)" 2>/dev/null; then
      printf '\n\033[1;32m=====================================================================\033[0m\n'
      printf '\033[1;32m  ABC AI Support Platform is running.\033[0m\n'
      printf '  Open:      %s\n' "$URL"
      printf '  API docs:  %s/docs\n' "$URL"
      printf '  Log in:    manager@abcfin.com / manager123   (more accounts in README)\n'
      printf '  Stop:      Ctrl + C\n'
      printf '\033[1;32m=====================================================================\033[0m\n\n'
      exit 0
    fi
    sleep 1
  done
) &

say "Starting the app on port ${PORT}..."
cd "$ROOT/backend"
exec "$VENV/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
