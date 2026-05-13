#!/usr/bin/env bash
# Vessel Ops AI — Desktop Companion Launcher (macOS / Linux)
#
# HOW TO OPEN A TERMINAL:
#   macOS: Press Cmd+Space, type "Terminal", press Enter
#          Then drag this file into the Terminal window and press Enter
#   Linux: Right-click the desktop → "Open Terminal"
#          Then type: bash /path/to/vessel-ops-ai/scripts/start.sh
#
# Run from the repo root:
#   bash scripts/start.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}▶${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
error() { echo -e "${RED}✗${NC} $*" >&2; }

# ── Pre-flight: venv must exist (installer must have run first) ───────────────
if [ ! -d ".venv" ]; then
  error "Virtual environment not found. Run the installer first:"
  error "  bash scripts/install.sh"
  exit 1
fi

# ── Pre-flight: frontend must be built ────────────────────────────────────────
if [ ! -f "frontend_out/index.html" ]; then
  error "Frontend not built. Run the installer first:"
  error "  bash scripts/install.sh"
  exit 1
fi

# ── Activate Python environment ───────────────────────────────────────────────
# shellcheck disable=SC1091
source .venv/bin/activate

# ── Ollama check ──────────────────────────────────────────────────────────────
if command -v ollama &>/dev/null && curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  info "Ollama is running."
else
  warn "Ollama is not running — AI features will be unavailable."
  warn "Start the Ollama app from your Applications menu (or run 'ollama serve'),"
  warn "then restart this script."
  warn "Continuing anyway — the app will load but AI replies won't work."
  echo ""
fi

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
  info "Seeding database with demo data..."
  python3 -m scripts.seed
fi

# ── Local IP for multi-device access ─────────────────────────────────────────
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null \
  || hostname -I 2>/dev/null | awk '{print $1}' \
  || echo "127.0.0.1")

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
  echo ""
  info "Shutting down..."
  kill "$UVICORN_PID" 2>/dev/null || true
}
trap cleanup INT TERM

# ── Launch backend (serves frontend_out statically) ───────────────────────────
info "Starting Vessel Ops AI on port 8000..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

# Give uvicorn a moment to start, then open browser
sleep 2
if command -v open &>/dev/null; then
  open "http://localhost:8000" 2>/dev/null || true   # macOS
elif command -v xdg-open &>/dev/null; then
  xdg-open "http://localhost:8000" 2>/dev/null || true  # Linux
fi

# ── Print access info ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Vessel Ops AI is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Open:      ${GREEN}http://localhost:8000${NC}"
echo -e "  On tablet: ${YELLOW}http://${LOCAL_IP}:8000${NC}  (same Wi-Fi network)"
echo -e "  API docs:  http://localhost:8000/docs"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

wait "$UVICORN_PID"
