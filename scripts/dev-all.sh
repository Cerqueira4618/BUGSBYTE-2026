#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

cd "$BACKEND_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install -r requirements.txt >/dev/null

uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Backend running on http://localhost:8000"

deactivate || true

cd "$ROOT_DIR"

export NVM_DIR="$HOME/.nvm"
if [[ -s "$NVM_DIR/nvm.sh" ]]; then
  # shellcheck disable=SC1091
  source "$NVM_DIR/nvm.sh"
  nvm use 20 >/dev/null || true
fi

npm install >/dev/null
npm run dev
