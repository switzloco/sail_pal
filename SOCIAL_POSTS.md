# Vessel Ops AI — Ready-to-post copy

Paste-and-go drafts for each platform. Each is tuned to that audience's
norms — don't cross-post verbatim, the framing matters more than the
content. **Replace `https://kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1778881323213`** with your final Kaggle entry link
before posting.

**Links to use:**
- Live app (no install): https://vessel-ops-494701.web.app/
- Desktop installer + source: https://github.com/switzloco/sail_pal
- Hackathon entry (for judges): https://kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1778881323213

**Link strategy:** Lead with the live app — it's the lowest-friction way to
convert a reader into someone who actually tries it and leaves a comment.
Add the Kaggle entry as a secondary CTA so supportive readers know where to
go for judging visibility. GitHub is always one click from the Kaggle page.

Recommended cadence: post HN + r/LocalLLaMA + r/sailing within a
4-hour window on a Tuesday–Thursday morning (9–11am ET) so any one
hit amplifies the others.

---

## 1. r/LocalLLaMA

**Title:**
Built an offline-first medical AI for ships — Gemma via Ollama, full WHO manual bundled, 75 MB Windows installer

**Body:**
Spent the last few months on Vessel Ops AI for the Gemma 4 Good Hackathon: an offline-first desktop app for vessels operating beyond shore-side medical and engineering support.

The whole thing runs on a sailor's laptop. No internet at runtime. `gemma4:e2b` via Ollama by default, `gemma4:e4b` available for heavier hardware.

There's also a hosted cloud preview if you want to try it without installing anything: https://vessel-ops-494701.web.app/

A few things I think this sub will appreciate:

- **RAG via SQLite FTS5, not embeddings.** Started with ChromaDB + sentence-transformers; the embedding model alone added ~1 GB to the installer. Replaced the whole RAG layer with SQLite FTS5 (built into stock Python) using BM25 ranking and a porter stemmer. 938 chunks of the WHO International Medical Guide for Ships ship as a 1.3 MB JSON that bootstraps into FTS5 on first launch. Bundle dropped ~99% with no measurable retrieval-quality loss — medical vocabulary is consistent enough that lexical search beats dense retrieval here.
- **Tauri 2 + PyInstaller in one installer.** Single 75 MB NSIS `.exe`, installs to `%LOCALAPPDATA%` per-user (no admin). Backend is uvicorn bound to `127.0.0.1` so Windows Firewall never prompts.
- **Citations every time.** Every medical chat hits the FTS5 index regardless of which screen you're on, and Gemma is prompted to cite `[WHO IMGS, p. XX]` inline.
- **Bundled the PDF too.** 2.2 MB for the full WHO manual so the crew can browse the source, not just the AI excerpts.

Stack: Next.js 14 (static export) + Tauri 2 + FastAPI + SQLite (WAL) + Ollama.

GitHub + desktop installer: https://github.com/switzloco/sail_pal
Kaggle entry: https://kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1778881323213

Happy to dive into any of the bundle-size or sidecar gotchas — the PyInstaller-orphan-process-bound-to-port-8000 saga alone was a journey.

---

## 2. Hacker News (Show HN)

**Title:**
Show HN: Vessel Ops AI – Offline medical and engineering assistant for ships

**Body:**
Hi HN — I built Vessel Ops AI for the Gemma 4 Good Hackathon. It's an offline-first desktop app that gives a vessel's Medical Person in Charge and Chief Engineer a second opinion when they're hundreds of miles from a doctor or shore-side tech support.

Everything runs locally on the ship's laptop via Ollama. The hackathon angle is Gemma — we use it for grounded medical triage against the WHO International Medical Guide for Ships (3rd ed.), engine fault analysis, and multimodal photo analysis of injuries or broken parts.

**Try the hosted preview** (cloud Gemma, no install): https://vessel-ops-494701.web.app/

A few engineering choices that might be interesting:

- **SQLite FTS5 for RAG.** We started with ChromaDB + sentence-transformers, then realized the embedding model added a gigabyte to the installer. Switched to FTS5 with BM25 — built into stock Python, no new deps, and on the WHO medical corpus the lexical search is competitive with dense retrieval. 938 chunks ship as 1.3 MB.
- **Tauri 2 + PyInstaller sidecar in a single NSIS installer.** Per-user install, no admin required, no network at install time. Backend is uvicorn bound to loopback so Windows Firewall never prompts.
- **Bundled the WHO PDF (2.2 MB).** The RAG queries chunks, but crew can also open the full source document from the sidebar. Offline-first means everything is local.

Code + desktop installer: https://github.com/switzloco/sail_pal
Kaggle: https://kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1778881323213

This is currently v0.1.0-rc7, Windows-only unsigned. Mac is in flight. Feedback very welcome — especially from anyone who's shipped a Tauri + Python sidecar app, since the PyInstaller bootloader process model on Windows took a few iterations to get right.

---

## 3. r/sailing  (alternate: r/liveaboard, same body)

**Title:**
Built an offline AI medical assistant for crews at sea — would love feedback from sailors

**Body:**
I'm a son of a Captain and we built Vessel Ops AI — an offline-first app for crews operating without internet. Runs entirely on your laptop, no Wi-Fi or sat link needed once it's installed.

The core idea: a vessel's MPIC shouldn't have to flip through a 400-page reference book in an emergency. The app is grounded in the WHO International Medical Guide for Ships (3rd Edition) — every answer cites a specific page in the WHO manual, and the full PDF is bundled so you can open it on the spot. It also helps the Chief Engineer with component troubleshooting and maintenance logs.

**Try it now** (no install, runs in your browser): https://vessel-ops-494701.web.app/

What I'm hoping for from this sub:
- Does the medical triage flow match how MPICs actually work in real emergencies?
- Engine-room use case: which manuals would you actually want loaded?
- Anyone running a similar setup at sea? Curious what tools you trust.

Desktop installer (Windows, Mac coming): https://github.com/switzloco/sail_pal/releases/latest

This is also a Gemma 4 Good Hackathon entry — if you find it useful, a comment or upvote on the Kaggle page helps: https://kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1778881323213

---

## 4. r/selfhosted

**Title:**
Vessel Ops AI — offline-first medical & engineering assistant. Zero phone-home, ships as a 75 MB Windows installer

**Body:**
Sharing a project that fits the self-hosted ethos pretty hard. Built for the Gemma 4 Good Hackathon.

**The pitch:** a single installer that gives you a local AI assistant for maritime medical and engineering ops. The "self-hosted" angle:

- All inference is local via Ollama (`gemma4:e2b` default, larger models supported).
- No telemetry. No accounts. No phone-home. Uvicorn binds 127.0.0.1 only.
- SQLite (WAL mode) for all data; lives in `%APPDATA%/VesselOpsAI/`. Easy to back up, easy to migrate.
- RAG runs on SQLite FTS5 — no separate vector DB, no embedding service. The 938-chunk WHO medical reference ships in the installer.
- The full WHO PDF (2.2 MB) is bundled so you have the source, not just AI excerpts.

Single 75 MB NSIS `.exe`, installs to `%LOCALAPPDATA%` per-user (no admin). Ollama is a separate one-time install. Mac build coming.

**Hosted preview** (cloud mode, for evaluation): https://vessel-ops-494701.web.app/
**Desktop installer + source**: https://github.com/switzloco/sail_pal
**Kaggle entry**: https://kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1778881323213

---

## 5. dev.to (long-form republish)

**Title:**
How I cut a 1.2 GB AI installer to 75 MB by killing the embedding model

**Tags:** `gemma`, `tauri`, `python`, `localfirst`

**Body:**
*(Paste the full Kaggle writeup here, with one additional opening hook paragraph framing the bundle-size problem as the through-line. Add a footer with both links:*

*"Try the hosted preview: https://vessel-ops-494701.web.app/ — or download the offline desktop installer from the GitHub releases page. Built for the Gemma 4 Good Hackathon. Full notebook + judging here: https://kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1778881323213")*

The dev.to audience responds to "I shipped X, here's what I learned" framing. Lead with the FTS5-vs-embeddings trade-off, walk through the Tauri + PyInstaller sidecar packaging, and close on the offline-first architecture wins.

---

## DM / direct outreach template (for 5–10 well-connected people)

> Hey [name] — long shot but: shipped a side project for the Gemma 4 Good Hackathon. It's an offline-first medical AI for ships, runs entirely on a laptop, bundles the full WHO medical manual. You can try the hosted version instantly here: https://vessel-ops-494701.web.app/ — if you find it interesting, a look at the Kaggle entry helps with judging visibility: https://kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1778881323213. Honest take welcome — I trust your eye on [the technical / maritime / AI] side.

Personalize one line per recipient. Five thoughtful DMs beat fifty broadcast.

---

## What NOT to do

- **Don't cross-post the same body** to multiple subreddits. Mods notice; karma loss is worse than no post.
- **Don't post to r/MachineLearning** — self-promo is banned outside Saturday threads.
- **Don't ask for upvotes explicitly** on HN or LocalLLaMA — instant flag.
- **Don't link only to GitHub.** The live app converts readers; the Kaggle entry is what gets judged. Both belong in every post.
- **Don't post Friday afternoon or weekend.** HN front-page traction is worst on Saturdays.
