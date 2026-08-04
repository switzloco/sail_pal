# CLAUDE.md — Vessel Ops AI

Agent instructions and project context. Read this before making changes.

---

## Project Overview

Vessel Ops AI is an offline-first AI assistant for maritime medical emergencies and vessel inventory. It runs on a laptop via Ollama (Gemma 4), with a FastAPI backend and Next.js frontend. There is also a hosted web version on Firebase/Cloud Run.

**Scope: two pillars, AI-forward.** The product is deliberately pared back to
**Medical** (chat guidance, crew records, health log) and **Inventory**
(components, spares, maintenance log). Chat is the primary surface — the
dashboard and sidebar lead with it. `/study` (MPIC Study) and `/trivia` still
build and still work if you navigate to them directly, but they are hidden from
navigation and must not be re-added to the dashboard or sidebar. Don't add a
third pillar without a deliberate decision to widen scope.

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
4. **mode_state is in-memory** on Cloud Run — it resets on cold start. This is a known limitation. Don't persist mode in the DB without careful thought. Note this applies to the *AI mode* only; vessel records are durable in Firestore (rule 7).
5. **Service worker** (`frontend/public/sw.js`) must skip cross-origin requests: `if (url.origin !== self.location.origin) return;` — without this it crashes on Cloud Run API calls.
6. **RAG grounds, it never gates.** `CITATION_INSTRUCTIONS` must never tell the model to refuse when the excerpts don't match. The old wording ("say 'I do not have information on that in my current library'") made BM25 near-misses produce a dead-end refusal on ordinary clinical questions — the single worst bug this app has had. Retrieval is keyword-based and *will* miss; the model must fall back to general knowledge and say so. The one hard limit that stays: never state a dosage or torque value that isn't in an excerpt. Guarded by `backend/tests/test_ai_routing.py` and `test_chat_endpoint.py`.
7. **Storage follows the deployment, not the AI-mode toggle.** `backend/store/` has two backends behind one interface: `SqlStore` (desktop, offline) and `FirestoreStore` (hosted). The choice comes from `settings.use_firestore`, which defaults to `CLOUD_MODE` — **never** from `mode_state`. A user switching the hosted app to "local" AI mode is choosing a model, and must not silently move their vessel records onto the ephemeral `/tmp` SQLite that Cloud Run erases on cold start. Both backends are held to the same behaviour by `backend/tests/test_store_parity.py`, which runs every test twice.
8. **Authorization lives in `backend/auth.py`, not in Firestore rules.** The backend uses the Admin SDK, which bypasses security rules by design, so `firestore.rules` denies all direct client access and the API is the only way in. `require_auth` defaults to `CLOUD_MODE`: hosted requires a verified Firebase ID token, desktop doesn't (that database is already scoped by physical access to the laptop). A caller who isn't a member of a vessel gets **404, not 403** — probing must not distinguish a real boat from a fake one. Never trust `vessel_id` from a request body; scope writes to `access.vessel_id`.
9. **Inventory is injected into every chat turn.** `_inventory_context()` in `backend/routers/ai.py` inlines the vessel's components and spares from the ship's own DB, and `INVENTORY_GROUNDING` marks it authoritative. This is what lets the assistant answer "do we have a spare impeller?" and write repair steps against spares actually held. Capped at `_INVENTORY_PROMPT_LIMIT`.

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
# Must pass: 231 tests, ≥60% coverage
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
- **Model routing is user-overridable**: `POST /api/ai/chat` takes `model_choice` (`auto` | `medical` | `general`); `GET /api/ai/models` describes the options for the chat picker. Auto-routing is medical-first — a clinical keyword vetoes demotion to general, so "what's in the medical stores for chest pain" stays medical. Keep new inventory keywords in `_GENERAL_INTENT_KEYWORDS` specific; generic phrases like "on board" appear constantly in medical questions and will mis-route them.
- **Chat context hand-off**: detail pages preselect chat context via `sessionStorage` (`frontend/src/lib/chatContext.ts`), not query params — the frontend is a static export, where `useSearchParams` needs a Suspense boundary on every consuming page.
- **Mac Ollama detection**: Use `ollama --version` not `which ollama` — macOS can have a stub in PATH that doesn't actually work.
- **MS Store Python**: `Get-Command python` on Windows may return a Store stub. Check if the path contains `WindowsApps` and fail with a clear message.
- **`/welcome/setup` vs `/setup`**: The setup page lives at `/welcome/setup`. Any link to `/setup` is a 404.
- **Cold start mode reset**: Cloud Run resets `mode_state` in-memory on cold start. If a user set local mode and sees cloud mode again, it's expected behavior — surface this clearly rather than silently re-defaulting.
