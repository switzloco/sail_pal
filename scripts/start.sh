#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}▶${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
error() { echo -e "${RED}✗${NC} $*"; }

# ── Ollama check (advisory — not required for Phase 1) ───────────────────────
if command -v ollama &>/dev/null && ollama list &>/dev/null 2>&1; then
  info "Ollama is running."
else
  warn "Ollama not detected. AI queries will return mock responses until Phase 2."
  warn "To enable: install Ollama, run 'ollama pull gemma4:12b', then restart."
fi

# ── Python environment ────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  info "Creating Python virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

info "Installing/verifying Python dependencies..."
pip install -q -r backend/requirements.txt

# ── Database setup ────────────────────────────────────────────────────────────
mkdir -p backend/data backend/data/uploads

info "Running database migrations..."
alembic upgrade head

# Seed if vessels table is empty
VESSEL_COUNT=$(python3 -c "
import sys; sys.path.insert(0,'.')
from backend.db.database import SessionLocal
from backend.db.models import Vessel
db = SessionLocal()
print(db.query(Vessel).count())
db.close()
" 2>/dev/null || echo "0")

if [ "$VESSEL_COUNT" -eq "0" ]; then
  info "Seeding database with MV Resolute demo data..."
  python3 -m scripts.seed
fi

# ── Local IP for multi-device access ─────────────────────────────────────────
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null \
  || hostname -I 2>/dev/null | awk '{print $1}' \
  || echo "127.0.0.1")

# ── Frontend dependencies ─────────────────────────────────────────────────────
if [ ! -d "frontend/node_modules" ]; then
  info "Installing frontend dependencies (first run — this takes a minute)..."
  (cd frontend && npm install --silent)
fi

# ── Cleanup on exit ───────────────────────────────────────────────────────────
PIDS=()
cleanup() {
  echo ""
  info "Shutting down..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup INT TERM

# ── Launch backend ────────────────────────────────────────────────────────────
info "Starting backend on port 8000..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
PIDS+=($!)

sleep 1  # give backend a moment before frontend starts

# ── Launch frontend ───────────────────────────────────────────────────────────
info "Starting frontend on port 3000..."
(cd frontend && npm run dev -- -H 0.0.0.0 -p 3000) &
PIDS+=($!)

# ── Print access info ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Vessel Ops AI — MV Resolute${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Frontend:  ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend:   ${GREEN}http://localhost:8000${NC}"
echo -e "  API docs:  ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  LAN:       ${YELLOW}http://${LOCAL_IP}:3000${NC}  (other devices on same network)"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

wait
