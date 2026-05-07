# Deploy & Maintenance Notes - Sail Pal

This document captures tribal knowledge and fixes for common issues encountered during development and deployment of the Sail Pal AI Vessel Ops system.

## 🧠 AI & LLM (Ollama)
- **Model Names**: Local Ollama installations may use specific tags. Always check `ollama list` before updating `backend/config.py`. 
  - *Current working tags*: `gemma4:e2b` (Primary), `gemma4:e4b` (Scale/Critical).
  - *Previous mismatch*: `gemma4:12b` (Status: 404).
- **Streaming**: AI endpoints (`/api/ai/*`) use `StreamingResponse`. Ensure frontend fetch logic handles `ReadableStream` correctly and parses the `data: { "token": "..." }` SSE format.

## 🎨 Frontend (Next.js / React)
- **React-Markdown**: The installed version (v9+) **does not** accept `className` as a prop. 
  - *Fix*: Wrap `<ReactMarkdown>` in a `div` with the desired `prose` classes.
- **Lucide Icons**: When adding new UI elements, remember to import icons in each specific page. Common ones added recently: `Sparkles`, `GraduationCap`, `Gamepad2`, `Trophy`.
- **JSX Escaping**: Next.js builds will fail on unescaped entities. Use `&apos;` instead of `'` or `&quot;` instead of `"`.

## 💻 Environment & CLI
- **Shell Restrictions**: PowerShell execution policies on this machine often block `npm`, `git`, and `uv`.
  - *Solution*: Always wrap commands in `cmd /c` (e.g., `cmd /c "npm run build"`).
- **Python Management**: Use `uv` for all Python tasks. 
  - *Binary Path*: `C:\Users\nswitzer\.local\bin\uv.exe`.
  - *Execution*: `uv run python backend/main.py`.

## 🎮 Game & Training Logic
- **Scoring**: The `MPIC_STUDY_SYSTEM` and `TRIVIA_SYSTEM` prompts are designed to output specific markers like `Evaluation: [Score]/10`. The frontend regex `content.match(/Evaluation:\s*(\d+)\/10/i)` relies on this exact formatting for point accumulation.
- **Persistence**: Points and milestones are currently stored in `localStorage`. If migrating to a multi-vessel sync, move these to the `UserProgress` table in SQLite.
