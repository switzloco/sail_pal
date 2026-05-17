# Vessel Ops AI — Offline Quickstart

Keep this file. **Print it, save it to your Desktop, screenshot it.**
If you lose internet at sea, you'll need it to start the app.

---

## Before You Leave Port (checklist)

Do all of these **while you still have internet**:

- [ ] Run the installer (`install.bat` / `install.sh`) until it says "Install complete!"
- [ ] Run `start.bat` / `bash scripts/start.sh` and confirm `http://localhost:8000` opens
- [ ] In the app: complete the Offline Setup wizard (Ollama + Gemma 4 downloaded)
- [ ] Add your crew in the app
- [ ] Copy this file to your Desktop AND print a copy

---

## First-Time Install (do this with internet)

Set aside ~1 hour for the full setup (most of that is downloading the Gemma 4 model, ~8 GB). Speed depends on your internet.

### Windows

1. Install **Python 3.11+**: <https://www.python.org/downloads/windows/>
   During install, check **"Add Python to PATH"**.
   *(Use the python.org installer — not the Microsoft Store version.)*

2. Install **Node.js LTS** (20+): <https://nodejs.org/>

3. Install **Ollama**: <https://ollama.com/download/windows>
   Open it and wait for the llama icon in your system tray (bottom-right corner).

4. Download Vessel Ops AI: <https://github.com/switzloco/sail_pal>
   Click the green **Code** button → **Download ZIP** → unzip it.

5. Open the unzipped folder. Open the `scripts` subfolder.
   **Double-click `install.bat`.** A console window will open and run the installer.
   If Windows shows a SmartScreen warning, click **More info → Run anyway**.

   *(Fallback: open `cmd` in the scripts folder and run
   `powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1`.)*

6. When it finishes ("Install complete!"), go to **Every-Day Use** below.

### macOS / Linux

1. Install **Python 3.11+**:
   - macOS: <https://www.python.org/downloads/macos/>
   - Linux: `sudo apt install python3 python3-venv` (or your package manager)

2. Install **Node.js LTS** (20+): <https://nodejs.org/>

3. Install **Ollama**:
   - macOS: <https://ollama.com/download/mac> — open the app, wait for the llama icon in your menu bar
   - Linux: `curl -fsSL https://ollama.com/install.sh | sh`

4. Download and unzip Vessel Ops AI from <https://github.com/switzloco/sail_pal>.

5. Open Terminal in the unzipped folder and run:
   ```
   bash scripts/install.sh
   ```

6. When it finishes ("Install complete!"), go to **Every-Day Use** below.

---

## Every-Day Use (after first install)

### Windows

1. Open the **Ollama** app from your Start menu.
   Wait for the llama icon in your system tray (bottom-right corner).
2. Double-click **`start.bat`** inside the `scripts\` folder.
3. A browser window opens at `http://localhost:8000`. That's the app.
4. To stop: press `Ctrl+C` in the black terminal window.

### macOS / Linux

1. Open the **Ollama** app from Applications (macOS) or run `ollama serve` (Linux).
   Wait for the llama icon in the menu bar.
2. Open Terminal in the `vessel-ops-ai` folder and run:
   ```
   bash scripts/start.sh
   ```
3. Your browser opens automatically to `http://localhost:8000`.
4. To stop: press `Ctrl+C` in Terminal.

---

## Troubleshooting (no internet, things broke)

**Browser shows "site can't be reached":**
The server isn't running. Re-run `start.bat` (Windows) or `bash scripts/start.sh`
(Mac/Linux). The terminal should say `Uvicorn running on http://127.0.0.1:8000`.

**App loads but AI replies say "Ollama is not running" or similar:**
Open the Ollama app from Start menu / Applications. You should see the llama
icon within ~10 seconds. Then refresh the browser.

**AI replies say "model is not pulled":**
You need internet to download the model (~8 GB). Run the installer again
once you have connectivity: `install.ps1` or `bash scripts/install.sh`.

**`start.bat` says "Virtual environment not found":**
The installer never completed. Connect to internet and re-run the installer.

**Download was interrupted mid-way:**
Just re-run the installer — Ollama automatically resumes from where it left off.

**Where are my files?**
The database lives in `backend/data/vessel.db`. Back this up before long
voyages if you've entered crew, logs, or maintenance records.

---

## Quick Reference Card

```
═══════════════════════════════════════════════════
  VESSEL OPS AI — QUICK REFERENCE
═══════════════════════════════════════════════════
  START (Windows): Ollama app → double-click scripts\start.bat
  START (Mac/Lin): Ollama app → bash scripts/start.sh
  OPEN:            http://localhost:8000
  STOP:            Ctrl+C in the terminal window
───────────────────────────────────────────────────
  AI MODELS: gemma4:e2b (general / engine / maintenance)
             + Vessel Ops Gemma 4 WHO medical fine-tune (medical routes)
             both downloaded by installer
  DATABASE: backend/data/vessel.db  (back this up!)
═══════════════════════════════════════════════════
```
