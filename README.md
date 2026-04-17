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

## Run Locally

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
