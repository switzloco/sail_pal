#!/usr/bin/env bash
# Vessel Ops AI — Desktop Companion Installer (macOS / Linux)
#
# HOW TO OPEN A TERMINAL:
#   macOS: Press Cmd+Space, type "Terminal", press Enter.
#          Then type: bash ~/Downloads/sail_pal-main/scripts/install.sh
#          (adjust the path to wherever you unzipped the folder)
#   Linux: Right-click the desktop → "Open Terminal", then run:
#          bash /path/to/sail_pal/scripts/install.sh
#
# Run from the repo root:
#   bash scripts/install.sh
#
# After this finishes, run: bash scripts/start.sh

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
FINE_TUNED_MODEL="vessel-ops:maritime"
FINE_TUNED_HF="hf.co/vessel-ops-ai/gemma4-maritime-medical-GGUF"

# ── curl ──────────────────────────────────────────────────────────────────────
if ! command -v curl &>/dev/null; then
  fail "curl is required but not found. Install it first:
  macOS:  brew install curl
  Linux:  sudo apt install curl  (or  sudo dnf install curl)"
fi

# ── Python ────────────────────────────────────────────────────────────────────
info "Checking Python..."
if ! command -v python3 &>/dev/null; then
  fail "Python 3 is not installed. Install 3.11+ from https://www.python.org/downloads/ and re-run."
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
OLLAMA_OK=false
if command -v ollama &>/dev/null && ollama --version &>/dev/null 2>&1; then
  OLLAMA_OK=true
fi

if [ "$OLLAMA_OK" = "false" ]; then
  if [[ "$(uname)" == "Darwin" ]]; then
    warn "Ollama not found or not working."
    warn "  1. Download Ollama.app from: https://ollama.com/download/mac"
    warn "  2. Open it and wait for the llama icon in your menu bar"
    warn "  3. Re-run this script"
    fail "Ollama install required."
  else
    warn "Ollama not found. Installing via official script..."
    curl -fsSL https://ollama.com/install.sh | sh
    if ! command -v ollama &>/dev/null; then
      fail "Ollama install failed. Visit https://ollama.com/download for manual instructions."
    fi
  fi
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

# ── Ensure Ollama is running before pull ─────────────────────────────────────
info "Checking Ollama is running..."
if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  warn "Ollama is installed but not running."
  if [[ "$(uname)" == "Darwin" ]]; then
    warn "  → Open the Ollama app from Applications and wait for the llama icon in your menu bar."
  else
    warn "  → Run 'ollama serve' in a separate terminal."
  fi
  warn "  Then re-run this script."
  fail "Ollama not running."
fi

# ── Pull base model ───────────────────────────────────────────────────────────
if ollama list 2>/dev/null | grep -q "${MODEL%:*}"; then
  info "Model ${MODEL} already pulled ✓"
else
  info "Pulling ${MODEL} (~8 GB, one-time download — this may take up to 1 hour depending on internet speed)..."
  info "If interrupted, just re-run this script — Ollama resumes from where it left off."
  ollama pull "${MODEL}"
fi

# ── Pull fine-tuned maritime medical model (optional) ─────────────────────────
if ollama list 2>/dev/null | grep -q "${FINE_TUNED_MODEL%:*}"; then
  info "Maritime medical model already registered ✓"
else
  info "Attempting to download the WHO IMGS fine-tuned maritime medical model (~1.8 GB)..."
  info "This is optional — the app works with the base model if this fails."
  MODELFILE_PATH="$(mktemp)"
  cat > "${MODELFILE_PATH}" <<MODELFILE
FROM ${FINE_TUNED_HF}
SYSTEM """You are an expert maritime medicine assistant trained on the WHO International Medical Guide for Ships (3rd Edition). You provide accurate, concise medical guidance to ship officers managing emergencies at sea with no doctor available. Always cite the relevant WHO IMGS page number when referencing specific protocols."""
PARAMETER temperature 0.7
PARAMETER num_ctx 4096
MODELFILE
  if ollama create "${FINE_TUNED_MODEL}" -f "${MODELFILE_PATH}" 2>/dev/null; then
    info "Maritime medical model registered as '${FINE_TUNED_MODEL}' ✓"
  else
    warn "Could not pull fine-tuned model (network issue or model not yet published)."
    warn "The app will use the base '${MODEL}' model instead — fully functional."
  fi
  rm -f "${MODELFILE_PATH}"
fi

# ── Frontend build ───────────────────────────────────────────────────────────
if [ ! -f "frontend_out/index.html" ]; then
  info "Building frontend (one-time, ~2 minutes)..."
  (cd frontend && npm ci --silent && NEXT_PUBLIC_API_BASE="" WEB_EXPORT=1 npm run build --silent)
  if [ ! -f "frontend/out/index.html" ]; then
    fail "Frontend build failed — index.html not found. Check Node.js version (need ${NODE_MIN}+) and try again."
  fi
  cp -R frontend/out frontend_out
  info "Frontend built ✓"
else
  info "Frontend already built ✓"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Install complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "  Next step:  bash scripts/start.sh"
echo "  Then open:  http://localhost:8000"
echo ""

# ── Drop an offline-ready quickstart on the Desktop ──────────────────────────
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ] && [ -f "DESKTOP_QUICKSTART.md" ]; then
  cp "DESKTOP_QUICKSTART.md" "$DESKTOP_DIR/Vessel-Ops-Quickstart.md"
  info "Saved offline instructions to: $DESKTOP_DIR/Vessel-Ops-Quickstart.md"
  warn "IMPORTANT: Keep this file — you'll need it if you lose internet at sea."
fi
