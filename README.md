# Vessel Ops AI

> "When a crew member is injured 200 miles offshore, there is no internet, no doctor,
> and no second opinion. This application is the second opinion."

An offline-first AI assistant for the **Medical Person in Charge (MPIC)** and **Chief Engineer**
on vessels operating in deep-water environments. Runs entirely on a laptop — no cloud, no connectivity
required at sea. Powered by **Gemma 4 via Ollama**.

---

## Hackathon Context

Built for the **Gemma 4 Good Hackathon** (Kaggle × Google DeepMind, due May 18, 2026).

Prize targets:
- **Ollama Prize** ($10k) — best project using Gemma 4 via Ollama
- **Global Resilience Prize** ($10k) — offline disaster/emergency response
- **Health & Sciences Prize** ($10k) — medical decision support
- **Cactus Prize** ($10k) — local-first app with intelligent model routing

---

## Deployment

```
Laptop (MacBook, Windows, Linux)
  └── Ollama  →  gemma4:12b or gemma4:27b
  └── FastAPI backend  →  SQLite (WAL mode)
  └── Next.js frontend  →  http://localhost:3000

Other devices on the same LAN (optional):
  └── Browser  →  http://<laptop-ip>:3000
```

The laptop is the server. Any other device on the same Wi-Fi network can connect via
the browser — no installation required.

**Model selection by hardware:**

| RAM | Recommended model | Notes |
|-----|------------------|-------|
| 8–16 GB | `gemma4:12b` | Fits most MacBook Air / mid-range laptops |
| 32 GB+ | `gemma4:27b` | Mixture-of-experts, noticeably better medical reasoning |

---

## Tech Stack

**Frontend:** Next.js 14 (App Router) · TypeScript · Tailwind CSS · React Query

**Backend:** Python 3.11+ · FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · SQLite (WAL)

**AI:** Gemma 4 via Ollama (Phase 2) · ChromaDB RAG (Phase 2) · sentence-transformers

**Sync (roadmap):** Firebase Firestore — accumulates locally, pushes when in port

---

## Install

### For end users — download the app

Download the latest signed installer for your OS from the
[Releases page](https://github.com/switzloco/sail_pal/releases/latest):

| OS | File |
|----|------|
| macOS (Apple Silicon) | `Vessel.Ops.AI_<version>_aarch64.dmg` |
| macOS (Intel) | `Vessel.Ops.AI_<version>_x64.dmg` |
| Windows 10 / 11 | `Vessel.Ops.AI_<version>_x64-setup.exe` |

Double-click to install. On first launch the in-app setup wizard walks you
through installing Ollama and downloading the Gemma model (~8 GB, one-time).
No Terminal, no Git, no Python required.

> **macOS unsigned builds (beta testers):** the current builds are not signed
> with an Apple Developer certificate. First-launch workflow on macOS:
>
> 1. Drag `Vessel Ops AI.app` from the `.dmg` to `/Applications`.
> 2. Right-click the app → *Open* → *Open* in the warning dialog.
>
> If you instead see *"'Vessel Ops AI' is damaged and can't be opened"*
> (macOS 13+ quarantine on unsigned apps from the internet), open Terminal
> and run:
>
> ```bash
> xattr -cr /Applications/Vessel\ Ops\ AI.app
> ```
>
> Then launch normally. This is a one-time step per install.

---

## Run Locally (developer setup)

### Prerequisites

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com) (optional for Phase 1 — AI returns demo responses without it)

### First run

```bash
git clone https://github.com/switzloco/sail_pal.git
cd sail_pal

cp .env.example .env
# Edit .env if needed (model choice, LAN IP for NEXT_PUBLIC_API_BASE)

./scripts/start.sh
```

That's it. `start.sh` will:
1. Create a Python virtual environment and install dependencies
2. Run database migrations (Alembic)
3. Seed the database with MV Resolute demo data (first run only)
4. Install frontend dependencies (first run only)
5. Start the backend on port 8000 and frontend on port 3000
6. Print your LAN IP for access from other devices

### With Ollama (Phase 2 preview)

```bash
# Install Ollama: https://ollama.com
ollama pull gemma4:12b   # or gemma4:27b on 32GB+ machines
# Then ./scripts/start.sh as normal
```

---

### Building the desktop app locally

Requires **Rust** (`rustup.rs`) and **Node 20+** in addition to the
Python/Node prereqs above.

```bash
cd frontend
npm install

# Dev (hot reload — backend must be running separately via ./scripts/start.sh)
npm run tauri:dev

# Production installer for the current OS (output under src-tauri/target/release/bundle/)
npm run tauri:build
```

The bundled backend is a PyInstaller one-file binary built from
`backend/pyinstaller.spec` and staged into `src-tauri/binaries/` before the
Tauri build — the GitHub Actions `release.yml` workflow automates this for
CI builds on tag push.

---

## Accessing from Another Device on the Same LAN

`start.sh` prints the LAN URL at startup. On the other device:
1. Open a browser and navigate to `http://<printed-ip>:3000`
2. You'll see the full Vessel Ops AI interface

---

## Project Status

| Feature | Status |
|---------|--------|
| Crew roster | ✅ Phase 1 |
| Health event log | ✅ Phase 1 |
| Component inventory | ✅ Phase 1 |
| Maintenance log | ✅ Phase 1 |
| AI medical query (mock SSE) | ✅ Phase 1 |
| AI component analysis (mock SSE) | ✅ Phase 1 |
| Ollama / Gemma 4 integration | 🔜 Phase 2 |
| ChromaDB RAG (medical + engine manuals) | 🔜 Phase 2 |
| Multimodal image analysis | 🔜 Phase 2 |
| Firebase sync (port-side) | 🔜 Phase 2 |

---

## AI Disclaimer

Every AI response includes:

> *AI-generated guidance. Verify against physical manuals. Contact rescue services if situation is life-threatening.*
