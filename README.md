# Vessel Ops AI

> "When a crew member is injured 200 miles offshore, there is no internet, no doctor, and no second opinion. This application is that second opinion."

An offline-first AI assistant for the **Medical Person in Charge (MPIC)** and **Chief Engineer** on vessels operating in deep-water environments. Runs entirely on a ship's laptop — no cloud, no connectivity required at sea. Powered by **Gemma 4 via Ollama**.

**[→ Live demo (no install)](https://vessel-ops-494701.web.app/)** · Built for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon) · Kaggle × Google DeepMind 2026

---

## What makes this real

Most offline medical AI demos run in a notebook and simulate everything. This doesn't.

| | Vessel Ops AI | Typical hackathon demo |
|---|---|---|
| **Knowledge base** | 938 chunks from the actual [WHO IMGS 3rd Ed. PDF](backend/data/manuals/WHO_IMGS_3rd_Edition.pdf) | Manually typed summaries |
| **Fine-tuned model** | Gemma 4 E2B fine-tuned on 900+ WHO IMGS Q&A pairs via Unsloth — real weights on HuggingFace | Config file saved to disk |
| **Installer** | Single `.exe` / `.dmg`, no admin rights, no terminal | Gradio link that expires |
| **Hardware tools** | Real Ollama local inference, real SQLite | `random.randint()` |
| **At-sea use** | Works with zero internet after install | Requires cloud API |

---

## Hackathon tracks

| Track | Prize | Why we qualify |
|-------|-------|---------------|
| **Unsloth** | $10k | Gemma 4 E2B fine-tuned on WHO IMGS corpus using Unsloth — real weights, real eval |
| **Ollama** | $10k | Entire offline inference stack runs via Ollama, including the fine-tuned model |
| **Health & Sciences** | $10k | WHO IMGS-grounded medical triage, multimodal injury analysis |
| **Global Resilience** | $10k | Offline-first, edge-deployed, works at sea with no connectivity |

---

## Architecture

```
Ship's laptop (offline at sea)
├── Ollama
│   ├── vessel-ops:maritime   ← Gemma 4 E2B fine-tuned on WHO IMGS (preferred)
│   └── gemma4:e2b            ← base fallback if fine-tune not pulled
├── FastAPI backend           ← Python 3.11, SQLite WAL, Alembic
│   └── SQLite FTS5 RAG       ← 938 chunks, BM25 ranking, porter stemmer
│       └── WHO_IMGS_3rd_Edition.pdf  (bundled — 2.2 MB)
└── Next.js frontend          ← static export served by uvicorn on :8000

Cloud preview (judges / demo)
├── Cloud Run backend         ← same FastAPI, CLOUD_MODE=true
│   └── Google AI Studio      ← Gemma-4-26b when Ollama unreachable
└── Firebase Hosting frontend ← https://vessel-ops-494701.web.app
```

---

## Fine-tuned model

The `vessel-ops:maritime` model is Gemma 4 E2B fine-tuned on ~900 WHO IMGS question-answer pairs generated from the actual 3rd Edition PDF using Unsloth QLoRA on a Kaggle T4 GPU.

- **Notebook:** [`notebooks/unsloth_finetune.ipynb`](notebooks/unsloth_finetune.ipynb)
- **Weights:** `hf.co/vessel-ops-ai/gemma4-maritime-medical-GGUF`
- **Eval:** Page citation accuracy on 50 held-out WHO IMGS questions

The installer attempts to pull this model automatically. If the pull fails (offline install, bandwidth constraints), the app transparently falls back to base `gemma4:e2b` — zero user-facing error.

---

## Install (end users — no terminal needed)

Download from the [Releases page](https://github.com/switzloco/sail_pal/releases/latest):

| OS | File |
|----|------|
| macOS (Apple Silicon) | `Vessel.Ops.AI_<version>_aarch64.dmg` |
| macOS (Intel) | `Vessel.Ops.AI_<version>_x64.dmg` |
| Windows 10/11 installer | `Vessel.Ops.AI_<version>_x64-setup.exe` — no admin rights needed |
| Windows 10/11 portable | `Vessel-Ops-AI_<version>_x64_portable.zip` — run from USB stick |

Double-click to install. The in-app setup wizard handles Ollama and model download (~8 GB, one-time). No terminal, no Git, no Python.

**Script install (macOS / Linux):**
```bash
git clone https://github.com/switzloco/sail_pal.git && cd sail_pal
bash scripts/install.sh   # pulls Ollama, base model, fine-tuned model, builds frontend
bash scripts/start.sh     # runs migrations, seeds DB, opens http://localhost:8000
```

---

## Repo structure

```
backend/
  ai/               ← Ollama client (model fallback logic), Gemini fallback, image parser
  data/manuals/     ← WHO_IMGS_3rd_Edition.pdf (the actual source document)
  routers/          ← FastAPI routes: ai, crew, health, components, setup
  tests/            ← 113 tests, ≥60% coverage
notebooks/
  unsloth_finetune.ipynb   ← Kaggle-ready fine-tune notebook (Unsloth + QLoRA)
  generate_qa_dataset.ipynb← WHO IMGS → Q&A pairs generation
scripts/
  install.sh / install.ps1 ← installs base model + fine-tuned model (optional, graceful fallback)
  start.sh / start.bat     ← runs migrations, seeds, launches on :8000
frontend/
  src/app/          ← Next.js App Router pages
  src-tauri/        ← Tauri 2 desktop wrapper (PyInstaller sidecar)
```

---

## Running tests

```bash
python -m pytest backend/tests/ -q
# 113 tests, ≥60% coverage required
```

---

## Tech stack

**Frontend:** Next.js 14 (App Router) · TypeScript · Tailwind CSS  
**Backend:** Python 3.11 · FastAPI · SQLAlchemy 2.0 · Alembic · SQLite WAL  
**AI:** Gemma 4 via Ollama (local) · Google AI Studio (cloud preview) · SQLite FTS5 RAG (BM25 + porter stemmer)  
**Desktop:** Tauri 2 · PyInstaller · NSIS  
**Infra:** Cloud Run · Firebase Hosting · GCP Cloud Build  

---

## AI disclaimer

Every AI response includes:

> *AI-generated guidance. Verify against physical manuals. Contact rescue services if situation is life-threatening.*
