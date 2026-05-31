# CLAUDE.md — Vessel Ops AI

Agent instructions and project context. Read this before making changes.

---

## Project Overview

Vessel Ops AI is an offline-first AI assistant for maritime medical emergencies and engineering ops. It runs on a laptop via Ollama (Gemma 4), with a FastAPI backend and Next.js frontend. There is also a hosted web version on Firebase/Cloud Run.

**Two deployment modes:**
- **Desktop companion** (`server_is_local=true`): FastAPI + SQLite on the user's laptop, Ollama on the same machine, frontend served statically from `frontend_out/` via uvicorn on port 8000.
- **Hosted web** (`server_is_local=false`): Cloud Run backend (CLOUD_MODE=true), Firebase Hosting frontend, Ollama NOT reachable (different localhost).

The `server_is_local` flag (`not settings.cloud_mode`) controls which UI paths are shown to the user. Always check it before assuming Ollama is accessible.

---

## Tech Stack

- **Backend:** FastAPI · SQLite (WAL) · SQLAlchemy · Alembic · httpx · uvicorn
- **Frontend:** Next.js 14 (App Router) · TypeScript · Tailwind CSS
- **AI:** Ollama for local mode — `gemma4:e2b` for general/engine/maintenance/trivia, `hf.co/nswitzer/gemma4-maritime-medical-GGUF` (Unsloth WHO fine-tune, `MODEL_MEDICAL` env) for medical routes · Google Gemini via API for cloud mode
- **Infra:** Cloud Run (backend) · Firebase Hosting (frontend) · GCP Cloud Build · Container Registry

---

## Key Architectural Rules

1. **`server_is_local` everywhere**: When `server_is_local=false`, the backend cannot reach the user's Ollama. Web UI must show desktop companion install instructions, not a server-side status checklist.
2. **Port 8000 only** for the desktop companion. `scripts/start.sh` runs uvicorn on 8000; it serves `frontend_out/` as static files. Do NOT start a separate npm dev server.
3. **`frontend_out/`** is the pre-built Next.js static export used by the desktop companion. The hosted web version is built separately in Cloud Build and deployed to Firebase.
4. **mode_state is in-memory** on Cloud Run — it resets on cold start. This is a known limitation. Don't persist mode in the DB without careful thought.
5. **Service worker** (`frontend/public/sw.js`) must skip cross-origin requests: `if (url.origin !== self.location.origin) return;` — without this it crashes on Cloud Run API calls.
6. **Fleet Mechanic is cloud-only**: Trace *capture* (`backend/ai/trace.py`) runs everywhere, offline, with zero new deps — never break this. The Arize upload + Gemini eval (`backend/eval/`) only run dockside when `ARIZE_*` / `GOOGLE_API_KEY` are set; the optional SDK lives in `backend/requirements-fleet.txt` and must stay out of the edge build. Trace capture failures are swallowed by design — observability must never break a medical answer at sea.

---

## Fleet Mechanic (offline trace eval)

Catches medical hallucinations in the offline model before the vessel sails again. Full architecture in `FLEET_MECHANIC.md`. The loop: every offline inference is captured as an `ai_traces` row → on dock sync the `run_fleet_mechanic` agent replays them into Arize, runs a Gemini LLM-as-judge eval (`correct`/`unsupported`/`hallucinated`/`unsafe`), and queues a `prompt_patches` row for any failure → the vessel pulls queued patches via `GET /api/traces/patches/pending` before departure.

- **Demo:** `python scripts/fleet_mechanic_demo.py --simulate` (self-contained, no keys needed).
- **Fail closed:** off-rubric judge responses default to `unsupported` so a human reviews — never silently trust a trace.
- **Portable traces:** `ai_traces.vessel_id`/`crew_id` are plain strings (not FKs) so the cloud can ingest a boat it has no relational row for.

---

## CI/CD Pipeline (`cloudbuild.yaml`)

Runs on every push to `main`. Steps:
1. Docker build → push backend image to Container Registry
2. Deploy backend to Cloud Run (us-west1, `--min-instances=0`)
3. Capture live Cloud Run URL
4. `npm ci && npm run build` for the frontend (bakes in the Cloud Run URL)
5. `firebase deploy --only hosting`

**Build time: ~20 minutes.** This is expensive and slow.

### Build caching (implemented)

`cloudbuild.yaml` pulls `:latest` before each Docker build (`allowFailure: true` for the first run) and passes `--cache-from` to reuse unchanged layers. The frontend `npm ci` uses a mounted cache volume. Expected savings: **10–12 minutes per build** (~50% cost reduction).

---

## Running Tests

```bash
# Backend (from repo root)
python -m pytest backend/tests/ -q
# Must pass: 113 tests, ≥60% coverage
```

Frontend has no automated tests — verify manually after UI changes.

---

## Desktop Companion Scripts

| Script | Purpose |
|--------|---------|
| `scripts/install.sh` | macOS/Linux: checks Python 3.11+, Node 20+, Ollama; installs deps; pulls model; builds frontend |
| `scripts/install.ps1` | Windows PowerShell equivalent; detects MS Store Python stub |
| `scripts/start.sh` | macOS/Linux launcher: activates venv, runs migrations, seeds DB, starts uvicorn on port 8000, opens browser |
| `scripts/start.bat` | Windows double-click launcher |

The installer copies `DESKTOP_QUICKSTART.md` to the user's Desktop. Keep that file accurate and non-technical — it's the only resource sailors have at sea with no internet.

---

## Common Gotchas

- **ESLint kills the build**: Next.js runs ESLint during `npm run build`. Unused imports, unescaped `"` in JSX (`&ldquo;`/`&rdquo;`), and `<img>` instead of `<Image />` are all hard errors.
- **Ollama model names**: UI should say "Gemma 4". Technical identifiers (`gemma4:e2b`, `hf.co/nswitzer/gemma4-maritime-medical-GGUF`) belong only in scripts and backend config. The split-routing pattern is: `model_primary` for general routes, `effective_medical_model` (→ `model_medical` or `model_primary`) for medical routes.
- **Mac Ollama detection**: Use `ollama --version` not `which ollama` — macOS can have a stub in PATH that doesn't actually work.
- **MS Store Python**: `Get-Command python` on Windows may return a Store stub. Check if the path contains `WindowsApps` and fail with a clear message.
- **`/welcome/setup` vs `/setup`**: The setup page lives at `/welcome/setup`. Any link to `/setup` is a 404.
- **Cold start mode reset**: Cloud Run resets `mode_state` in-memory on cold start. If a user set local mode and sees cloud mode again, it's expected behavior — surface this clearly rather than silently re-defaulting.
