# Vessel Ops AI

> "When a crew member is injured 200 miles offshore, there is no internet, no doctor,
> and no second opinion. This application is the second opinion."

An offline-first AI assistant for vessels operating beyond the reach of shore support.
It runs entirely on a laptop — no cloud, no connectivity required at sea — and answers
from the **WHO International Medical Guide for Ships** plus your own vessel's inventory.

Powered by **Gemma 4 via Ollama**.

---

## What it does

Two jobs, deliberately:

**Medical.** Describe a symptom and get assessment questions, red flags, immediate care
steps, and when to escalate to TMAS. Answers are grounded in the WHO IMGS (3rd Edition),
cited by page, and informed by the crew member's own allergies and medical history.

**Inventory.** Every component and spare aboard, searchable by part number, location, or
spare. The assistant reads this inventory on every question, so it knows what you actually
carry before it recommends a repair — and says plainly when a job needs a part you don't have.

Chat is the front door. Everything else exists to give it better context.

---

## Install

### For crew — download the app

Grab the installer for your OS from the
[Releases page](https://github.com/switzloco/sail_pal/releases/latest):

| OS | File | Notes |
|----|------|-------|
| macOS (Apple Silicon) | `Vessel.Ops.AI_<version>_aarch64.dmg` | Drag to `/Applications` |
| macOS (Intel) | `Vessel.Ops.AI_<version>_x64.dmg` | Drag to `/Applications` |
| Windows 10 / 11 — installer | `Vessel.Ops.AI_<version>_x64-setup.exe` | Per-user install, **no admin rights needed** — lives in `%LOCALAPPDATA%` |
| Windows 10 / 11 — portable | `Vessel-Ops-AI_<version>_x64_portable.zip` | No install at all. Unzip anywhere (USB stick, Desktop) and double-click `Vessel Ops AI.exe` inside the folder. Keep `vessel-ops-backend.exe` next to it — the launcher spawns it as the local API. |

On first launch the in-app setup wizard walks you through installing Ollama and
downloading the models (~8 GB, one-time, needs internet). After that the app never
needs a connection again.

> **Do the model download in port.** The one-time ~8 GB pull is the only thing that
> requires internet. Everything after it runs on the laptop.

> **Locked-down work PC?** The installer needs no admin rights and makes no
> system-level changes. If your IT policy blocks installers entirely, use the
> portable `.zip`: unzip it (right-click → *Extract All*) and run
> `Vessel Ops AI.exe` from inside the extracted folder. Don't separate the two
> `.exe` files — the launcher spawns `vessel-ops-backend.exe` as a sibling process
> and won't find it otherwise. Ollama also installs per-user on Windows.

> **macOS unsigned builds:** current builds aren't signed with an Apple Developer
> certificate. Drag the app to `/Applications`, then right-click → *Open* →
> *Open* in the warning dialog. If you instead see *"'Vessel Ops AI' is damaged
> and can't be opened"* (macOS 13+ quarantine), run this once:
>
> ```bash
> xattr -cr /Applications/Vessel\ Ops\ AI.app
> ```

### Running from source

```bash
git clone https://github.com/switzloco/sail_pal.git
cd sail_pal
cp .env.example .env
./scripts/start.sh
```

`start.sh` creates the virtualenv, runs migrations, seeds demo data on first run,
and starts the app on **port 8000**. Open <http://localhost:8000>.

The laptop is the server. Any device on the same Wi-Fi — a tablet on the bridge, a
phone in the engine room — reaches it at `http://<laptop-ip>:8000`, no install needed.
`start.sh` prints that address at startup.

---

## How the AI works

### Two models, and you can override the choice

| Route | Model | Used for |
|-------|-------|----------|
| Medical | `hf.co/nswitzer/gemma4-maritime-medical-GGUF` | Symptoms, first aid, WHO protocols. Our Unsloth fine-tune on ~1,400 clinical Q&A pairs from the IMGS, Q4_K_M (~2 GB) |
| Ship & Inventory | `gemma4:e2b` | Components, spares, fault diagnosis, maintenance, regulations |
| Escalation (optional) | `gemma4:e4b` | 32 GB+ machines, for `critical` / `serious` severity |

Routing is automatic and medical-first — a clinical signal always wins, so
*"what's in the medical stores for chest pain"* stays on the medical model. When the
router gets it wrong, the **model picker in chat** overrides it for that turn, and the
choice sticks. Every answer carries a badge showing which route served it.

If the fine-tune isn't installed, the app says so in the picker rather than silently
falling back.

### Retrieval grounds answers — it never gates them

Medical questions retrieve the top-3 passages from the WHO IMGS index (SQLite FTS5,
BM25 ranking) and cite them by page. Engineering questions do the same against uploaded
technical manuals.

Keyword retrieval misses sometimes. When it does, the assistant answers from general
maritime medical knowledge and *says* the answer isn't from the onboard library — it
never returns a bare "I don't have that." The one hard limit: it will not state a drug
dosage or torque value that isn't in a retrieved passage, and will tell you which
reference to check instead.

### It knows what's aboard

Your components and spares are injected into every chat turn from the vessel's own
database and treated as authoritative. Ask "do we have a spare impeller?" and you get a
real answer, not a guess.

---

## Tech Stack

**Frontend:** Next.js 14 (App Router) · TypeScript · Tailwind CSS · React Query · Tauri (desktop)

**Backend:** Python 3.11+ · FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · SQLite (WAL)

**AI:** Gemma via Ollama (local) or Google AI Studio (hosted preview) · SQLite FTS5 RAG with BM25 ranking

**Knowledge:** *WHO International Medical Guide for Ships*, 3rd Edition — fully offline

---

## Hosted web version

A hosted build runs the app in **cloud mode**: Google AI Studio serves Gemma, so there's
no Ollama install, and records live in **Firestore** rather than on your laptop. Useful for
keeping a boat's log from a phone; **not** the way to use this at sea, since it needs
connectivity. A banner in the UI makes the mode obvious.

Hosted mode requires a sign-in. A vessel's records — crew, medical history, inventory —
are private to the accounts on that boat's membership list, and the owner can share access
with other crew. Enforcement is server-side in `backend/auth.py`; `firestore.rules` denies
all direct client access.

Stack: **Cloud Run** (backend) + **Firestore** (data) + **Firebase Auth** + **Firebase
Hosting** (frontend), built by `cloudbuild.yaml` on every push to `main`.

This repo publishes to the Hosting site **`vessel-ops-ai`**, not the project's default
site — see [`docs/DEPLOY_TARGETS.md`](docs/DEPLOY_TARGETS.md) for why, and for how to
split the backend too.

> **Setting this up yourself?** [`docs/FIREBASE_SETUP.md`](docs/FIREBASE_SETUP.md) has the
> console steps — provisioning Firestore, granting the Cloud Run service account access,
> enabling sign-in providers. Skip it and the hosted app builds with no sign-in, where
> every visitor shares one vessel.

<details>
<summary>Deployment setup</summary>

**Backend → Cloud Run**

1. In [Cloud Console](https://console.cloud.google.com), enable the **Cloud Build API**
   and **Cloud Run API**.
2. **Cloud Build → Triggers → Connect repository**, then create a trigger on `main`
   pointing at `cloudbuild.yaml`.
3. **Cloud Run → vessel-ops-backend → Edit & Deploy New Revision → Variables & Secrets**:
   ```
   GOOGLE_API_KEY = <key from aistudio.google.com/apikey>
   ```
   (`CLOUD_MODE=true` is already set by `cloudbuild.yaml`.)

Push to `main` and Cloud Build handles the rest.

**Frontend → Firebase Hosting**

```bash
npm install -g firebase-tools && firebase login
cd frontend
NEXT_PUBLIC_API_BASE=https://<your-cloud-run-url> WEB_EXPORT=1 npm run build
firebase deploy --only hosting
```

**Firestore + Auth** — see [`docs/FIREBASE_SETUP.md`](docs/FIREBASE_SETUP.md).

Cloud Run containers are stateless, so the selected AI mode resets on cold start.
Vessel records are not affected — those live in Firestore.

</details>

---

## Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com)

### Tests

```bash
python -m pytest backend/tests/ -q      # 234 tests, ≥60% coverage
```

The frontend has no automated tests — verify UI changes manually.

### Building the desktop app

Requires **Rust** (`rustup.rs`) in addition to the above.

```bash
cd frontend
npm install
npm run tauri:dev      # hot reload; run ./scripts/start.sh separately for the backend
npm run tauri:build    # installer for the current OS
```

The bundled backend is a PyInstaller one-file binary built from
`backend/pyinstaller.spec` and staged into `frontend/src-tauri/binaries/` before the
Tauri build. The `release.yml` workflow automates this on tag push.

See [`CLAUDE.md`](CLAUDE.md) for architecture rules and the gotchas worth knowing before
you change anything.

---

## Status

| Area | State |
|------|-------|
| Medical chat — WHO IMGS grounding, citations, crew context | Shipping |
| Inventory — components, spares, search, AI awareness | Shipping |
| Model routing + in-chat model picker | Shipping |
| Health & maintenance logs | Shipping |
| Multimodal image analysis | Shipping |
| Hosted mode: Firestore persistence + sign-in | Shipping |
| Boat sharing between accounts | API only — no UI yet |
| Desktop installers (macOS, Windows) | Beta — unsigned |
| Spare quantities & expiry tracking | Planned |
| Desktop ↔ hosted sync when back in port | Planned — the two stores are independent today |

MPIC study drills and trivia were built earlier and still work at `/study` and `/trivia`,
but they're no longer part of the main navigation — the app is focused on medical and
inventory.

---

## Disclaimer

Every AI response carries:

> *AI-generated guidance. Verify against physical manuals. Contact rescue services if
> situation is life-threatening.*

This is decision support, not a doctor. Contact TMAS for anything serious.

---

## Origins

Vessel Ops AI began as a submission to the Gemma 4 Good Hackathon (Kaggle × Google
DeepMind), built by Nick Switzer with Dr. Michael Switzer (medical advisor) and
Capt. Chris Oprzadek (Navy submarine officer, two Atlantic crossings). Those materials —
the writeup, video scripts, and launch posts — are archived under
[`docs/archive/hackathon/`](docs/archive/hackathon/).

The focus now is real use aboard real boats.
