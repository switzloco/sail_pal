# Kaggle Writeup: Vessel Ops AI

**Title:** Vessel Ops AI: Precision Assistance for Remote Operations
**Subtitle:** Bringing life-saving Gemma intelligence to austere, disconnected maritime environments.
**Tracks:** Main Track, Global Resilience, Health & Sciences, Ollama, Unsloth

## 1. The Problem: Isolation at Sea
When a crew member is injured 200 miles offshore, there is no internet connection, no doctor, and no opportunity for a second opinion. Vessels operate in environments where bandwidth is either non-existent or prohibitively expensive — a satellite call to shore-side telemedicine (TMAS) is the last line of defense, not the first. In an emergency, the Medical Person In Charge (MPIC) relies on static textbooks, prior training, and intuition. The same isolation extends to the engine room, where the Chief Engineer must diagnose complex machinery faults without OEM support or a search engine.

## 2. The Solution: Vessel Ops AI
Vessel Ops AI is an offline-first desktop application designed to serve as that critical second opinion. Powered entirely by Gemma running locally via Ollama on the ship's existing hardware, it requires zero cloud connectivity at sea. It provides AI-assisted medical triage grounded in the *WHO International Medical Guide for Ships* (3rd Edition) and aids engineering operations through intelligent component and maintenance analysis. A hosted preview running on Cloud Run + Firebase Hosting lets reviewers try the app without installing anything.

## 3. Architecture & Technical Choices
Our primary engineering constraint was absolute reliance on an offline environment with a one-click install that doesn't require administrator privileges or a network connection at runtime. The architecture is explicitly designed for local durability, low latency, and ease of deployment for non-technical crews.

* **AI Engine (Ollama + Gemma):** Local inference defaults to our Unsloth-finetuned `hf.co/vessel-ops-ai/gemma4-maritime-medical-GGUF` (Q4_K_M, ~2 GB) — the WHO-IMGS-specialised Gemma 4 described in §5 — pulled directly from HuggingFace by Ollama at install time. Vanilla `gemma4:e2b` is also pulled as a guaranteed fallback, and `gemma4:e4b` is available for higher-end hardware. Ollama was chosen for its efficient inference, robust local API, and cross-platform reliability. A cloud fallback via Google AI Studio (`gemma-4-26b-a4b-it`) is used by the hosted preview when no local Ollama is available.
* **Backend (FastAPI + SQLite WAL):** Python 3.11 + FastAPI behind uvicorn bound to `127.0.0.1` (no inbound network exposure, no Windows Firewall prompt). SQLite in Write-Ahead Logging mode provides a robust, concurrent, zero-config data store ideal for a single-laptop deployment. Alembic manages migrations.
* **Frontend (Next.js + Tauri 2):** Next.js 14 App Router exported as static HTML, wrapped by a Tauri 2 Rust launcher that spawns the Python backend as a PyInstaller-frozen sidecar. The result is a single NSIS installer (`.exe`) that installs to `%LOCALAPPDATA%` per-user — no admin privileges required, no network calls during install. v1 ships Windows-only; macOS and Linux are next.
* **Retrieval-Augmented Generation (SQLite FTS5):** Earlier iterations used ChromaDB + sentence-transformers, but the embedding model alone added ~1 GB to the installer. We replaced the entire RAG layer with SQLite FTS5 (built into stock Python) using BM25 ranking and a porter stemmer. The 938-chunk WHO IMGS index ships as a 1.3 MB JSON file that bootstraps into the FTS5 virtual table on first launch. Bundle size dropped ~99% with no measurable loss in retrieval quality on this corpus — medical vocabulary is consistent enough that lexical search beats dense retrieval here.
* **Bundled WHO Manual:** The full 2.2 MB *WHO IMGS 3rd Edition* PDF is bundled in the installer so crew can browse and print the source document offline at sea, not just receive AI-cited excerpts.
* **Offline-first sync queue:** Every database write at sea is mirrored into a local `sync_queue` table. Firebase Firestore export from that queue is the next milestone — the queue itself is the harder half of the problem and is already in place.

## 4. How We Used Gemma
Gemma is the core intelligence of Vessel Ops AI. We use it in three ways:

* **Grounded medical triage:** Every chat query — regardless of which screen the user is on — automatically retrieves the top 3 BM25-ranked passages from the WHO IMGS FTS5 index and includes them in the system prompt with explicit `[Source, p. XX]` citation markers. Gemma is instructed to use only the provided context and to cite the page on every claim, dramatically reducing hallucination on dosages and protocols.
* **Multimodal injury & component analysis:** When a crew member uploads a photo of an injury or a failing engine part, Gemma's multimodal capability classifies the observation and feeds the result back into the RAG step as additional query context.
* **Domain-specific personas:** Different code paths (medical chat, engine chat, MPIC study mode, trivia) apply different system prompts, all built on the same Gemma model. The MPIC study mode in particular acts as an interactive examiner that scores the user's responses 1–10 against established maritime medical protocols.

## 5. Domain Fine-tuning with Unsloth

The RAG layer grounds Gemma's responses in the WHO IMGS at inference time, but a general-purpose base model still has to *interpret* maritime medical prose it has never been optimised for. We address this with a purpose-built fine-tune targeting the Unsloth Special Technology Prize — and the resulting model ships as the **default** the installer pulls and selects, not an optional add-on.

**Dataset generation (`backend/scripts/generate_training_data.py`):** We convert the 938 WHO IMGS chunks into clinical Q&A pairs. Each chunk is passed to Gemini (acting as a subject-matter expert) with a prompt that asks for two realistic questions a ship officer might ask during an emergency, along with grounded answers that cite the source page. After filtering TOC and header-only chunks, this yields ~1,400 high-quality training examples in ShareGPT conversation format.

**Fine-tuning (`notebooks/unsloth_finetune.ipynb`):** We fine-tune `gemma-4-2b` using Unsloth + QLoRA (rank 16, RSLoRA scaling) on a Kaggle T4 GPU — the same class of hardware available on many modern vessels. Key choices:
* **4-bit quantised base + fp16 LoRA** — fits comfortably in 16 GB VRAM with sequence packing enabled
* **3 epochs, cosine LR schedule, effective batch 8** — enough to converge without overfitting on ~1,400 examples
* **GGUF export (Q4_K_M)** — the merged model is quantised and pushed to HuggingFace as `vessel-ops-ai/gemma4-maritime-medical-GGUF` in a format Ollama can pull directly (`ollama pull hf.co/vessel-ops-ai/gemma4-maritime-medical-GGUF`), keeping the end-user install path unchanged. Conversion follows Unsloth's standard pipeline: `llama.cpp` build → HF→GGUF f16 → Q4_K_M quantisation, all driven from `model.push_to_hub_gguf(...)` in the notebook.

**What the fine-tune adds:** The model internalises the WHO IMGS vocabulary, drug names, dosage patterns, and protocol structure. With RAG still enabled on top, the combination dramatically reduces hallucination on specific dosages and page-cited protocols compared to the base model. Without RAG, the fine-tuned model alone still outperforms the base on maritime medical Q&A — useful if the FTS5 index is unavailable or the query is too ambiguous for good retrieval.

**Reproducibility:** Weights and the training dataset are both public on HuggingFace. The Kaggle notebook is attached to this writeup and can be re-run end-to-end on a free T4 session in under 3 hours.

## 6. Challenges Overcame
* **Running frontier AI on "potato" hardware.** Many vessels run older laptops. `gemma4:e2b` was chosen specifically for its capability-to-size ratio — responses generate fast enough to be useful in an emergency on hardware that wouldn't fit a 12B+ model in RAM alongside the application.
* **Deployment for non-technical crews.** Installing Python, Node, and Ollama is beyond a typical crew member. We wrap the entire environment — Python interpreter, all dependencies, the FTS5 index, the WHO PDF — into a single NSIS-installed `.exe` that runs without admin rights. Ollama itself remains a separate one-time install, but the rest of the stack is invisible.
* **PyInstaller orphan processes.** PyInstaller `--onefile` builds run a bootloader that exec's the real Python interpreter; on Windows, killing the bootloader doesn't propagate to the child, so uvicorn keeps port 8000 bound after the GUI window closes. We reap orphan `vessel-ops-backend.exe` processes on every launch (`taskkill /F /IM`) before spawning, with a 500ms settle to let Windows release the port. Without this, the second launch silently fails to bind and the launcher would mistakenly report success because it's connecting to the orphan.
* **Service Worker survives app upgrades.** A service worker registered against `tauri://localhost` (actually `https://tauri.localhost` on Windows) survives across installer versions and serves cached HTML referencing chunk hashes that no longer exist in the new bundle. We had the new SW detect the Tauri origin and self-destruct on activate — clearing all caches, unregistering, and force-reloading any open windows — so users self-heal on first launch of the new version.
* **Sidecar packaging size.** Stripping torch, transformers, sentence-transformers, and ChromaDB from the PyInstaller spec cut the sidecar from ~1.2 GB to ~75 MB — small enough to ship without a code-signing certificate spend.

## 7. Conclusion
Vessel Ops AI proves that frontier intelligence doesn't have to be tethered to a data center. By bringing Gemma directly to the laptop in the wheelhouse — with a purpose fine-tuned maritime medical model, a WHO IMGS grounded RAG layer, a fully bundled installer, and a UI built for the realities of life at sea — we are giving maritime crews a second opinion they can trust when there is no one else to ask.
