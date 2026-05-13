#!/usr/bin/env bash
# Vessel Ops AI — Desktop Companion Installer (macOS / Linux)
#
# Run from the repo root:
#   bash scripts/install.sh
#
# Installs Ollama, sets up a Python venv, pulls the Gemma model, and builds
# the frontend. After this finishes, run `bash scripts/start.sh` to launch.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}▶${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
fail()  { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

PY_MIN_MAJOR=3
PY_MIN_MINOR=11
NODE_MIN=20
MODEL="gemma4:e2b"

# ── Python ────────────────────────────────────────────────────────────────────
info "Checking Python..."
if ! command -v python3 &>/dev/null; then
  fail "Python 3 is not installed. Install from https://www.python.org/downloads/ (need 3.11+)."
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=${PY_VER%.*}; PY_MINOR=${PY_VER#*.}
if (( PY_MAJOR < PY_MIN_MAJOR )) || { (( PY_MAJOR == PY_MIN_MAJOR )) && (( PY_MINOR < PY_MIN_MINOR )); }; then
  fail "Python ${PY_VER} is too old. Install 3.11+ from https://www.python.org/downloads/."
fi
info "Python ${PY_VER} ✓"

# ── Node.js ───────────────────────────────────────────────────────────────────
info "Checking Node.js..."
if ! command -v node &>/dev/null; then
  fail "Node.js is not installed. Install LTS from https://nodejs.org/ (need ${NODE_MIN}+)."
fi
NODE_MAJOR=$(node -v | sed 's/v//' | cut -d. -f1)
if (( NODE_MAJOR < NODE_MIN )); then
  fail "Node.js v${NODE_MAJOR} is too old. Install LTS (${NODE_MIN}+) from https://nodejs.org/."
fi
info "Node.js v${NODE_MAJOR} ✓"

# ── Ollama ────────────────────────────────────────────────────────────────────
info "Checking Ollama..."
if ! command -v ollama &>/dev/null; then
  warn "Ollama not found. Installing via official script..."
  if [[ "$(uname)" == "Darwin" ]]; then
    warn "On macOS, please download Ollama.app from https://ollama.com/download and then re-run this script."
    fail "Ollama install required."
  fi
  curl -fsSL https://ollama.com/install.sh | sh
fi
info "Ollama $(ollama --version 2>/dev/null | head -1) ✓"

# ── Python venv + backend deps ───────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  info "Creating Python virtual environment..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
info "Installing backend dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt

# ── Pull model ────────────────────────────────────────────────────────────────
info "Ensuring Ollama is running..."
if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  warn "Ollama isn't responding on localhost:11434."
  warn "Start the Ollama app (or run 'ollama serve' in another terminal) and re-run this script."
  fail "Ollama not running."
fi

if ollama list 2>/dev/null | grep -q "${MODEL%:*}"; then
  info "Model ${MODEL} already pulled ✓"
else
  info "Pulling ${MODEL} (~8 GB, one-time download)..."
  ollama pull "${MODEL}"
fi

# ── Frontend build ───────────────────────────────────────────────────────────
if [ ! -d "frontend_out" ] || [ ! -f "frontend_out/index.html" ]; then
  info "Building frontend (one-time)..."
  (cd frontend && npm ci --silent && NEXT_PUBLIC_API_BASE="" WEB_EXPORT=1 npm run build --silent)
  cp -R frontend/out frontend_out
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Install complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "  Run:  bash scripts/start.sh"
echo "  Then open: http://localhost:8000"
echo ""

# ── Drop an offline-ready quickstart on the Desktop ──────────────────────────
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ] && [ -f "DESKTOP_QUICKSTART.md" ]; then
  cp "DESKTOP_QUICKSTART.md" "$DESKTOP_DIR/Vessel-Ops-Quickstart.md"
  info "Saved offline instructions to: $DESKTOP_DIR/Vessel-Ops-Quickstart.md"
  warn "Keep this file! You'll need it if you lose internet at sea."
fi
