# Deploy & Maintenance Notes - Sail Pal

This document captures tribal knowledge and fixes for common issues encountered during development and deployment of the Sail Pal AI Vessel Ops system.

## 🧠 AI & LLM (Ollama)
- **Model Names**: Local Ollama installations may use specific tags. Always check `ollama list` before updating `backend/config.py`. 
  - *Current working tags*: `gemma4:e2b` (Primary), `gemma4:e4b` (Scale).
  - *Previous mismatch*: `gemma4:12b` and `gemma4:27b` were removed from docs/config — these tags returned 404 on Ollama.
- **Streaming**: AI endpoints (`/api/ai/*`) use `StreamingResponse`. Ensure frontend fetch logic handles `ReadableStream` correctly and parses the `data: { "token": "..." }` SSE format.

## 🎨 Frontend (Next.js / React)
- **React-Markdown**: The installed version (v9+) **does not** accept `className` as a prop. 
  - *Fix*: Wrap `<ReactMarkdown>` in a `div` with the desired `prose` classes.
- **Lucide Icons**: When adding new UI elements, remember to import icons in each specific page. Common ones: `Sparkles` (AI), `HeartPulse` (medical), `Package` (inventory), `ClipboardList` (maintenance).
- **JSX Escaping**: Next.js builds will fail on unescaped entities. Use `&apos;` instead of `'` or `&quot;` instead of `"`.

## 💻 Environment & CLI
- **Shell Restrictions**: PowerShell execution policies on this machine often block `npm`, `git`, and `uv`.
  - *Solution*: Always wrap commands in `cmd /c` (e.g., `cmd /c "npm run build"`).
- **Python Management**: Use `uv` for all Python tasks. 
  - *Binary Path*: `C:\Users\nswitzer\.local\bin\uv.exe`.
  - *Execution*: `uv run python backend/main.py`.

## 🧭 AI Routing & Grounding
- **Never let RAG gate an answer**: `CITATION_INSTRUCTIONS` must not instruct a refusal when retrieval misses. BM25 near-misses are routine, and the old "I do not have information on that in my current library" wording turned them into dead ends on ordinary clinical questions. Grounding yes, gating no. The one hard limit that stays: no dosage or torque value that isn't in a retrieved passage.
- **Routing is medical-first**: `_has_medical_intent` vetoes demotion to the general model. Keep new entries in `_GENERAL_INTENT_KEYWORDS` specific — generic phrases like "on board" appear in medical questions constantly and will mis-route them.
- **Model picker**: `POST /api/ai/chat` accepts `model_choice` (`auto` | `medical` | `general`); `GET /api/ai/models` describes the options. The picker overrides auto-routing per turn and persists in `localStorage`.
- **Inventory in every turn**: `_inventory_context()` inlines components + spares from the vessel DB, capped at `_INVENTORY_PROMPT_LIMIT`.

## 🕹️ Hidden surfaces (MPIC Study / Trivia)
These are no longer in the navigation but the code still builds and the routes still work.
- **Scoring**: The `MPIC_STUDY_SYSTEM` and `TRIVIA_SYSTEM` prompts output markers like `Evaluation: [Score]/10`. The frontend regex `content.match(/Evaluation:\s*(\d+)\/10/i)` relies on that exact formatting for point accumulation.
- **Persistence**: Points and milestones live in `localStorage`. If they ever come back and need multi-vessel sync, move them to a `UserProgress` table in SQLite.
