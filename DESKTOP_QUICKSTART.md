# Vessel Ops AI — Offline Quickstart

Keep this file. **Print it, save it to your Desktop, screenshot it.** If you
lose internet at sea, you'll need it to start the app.

---

## Every-Day Use (after first install)

### Windows
1. Open the **Ollama** app from your Start menu. Wait for the llama icon to
   appear in the system tray (bottom-right corner).
2. Double-click **`start.bat`** inside the `vessel-ops-ai\scripts\` folder.
3. A browser window opens at `http://localhost:8000`. That's the app.
4. To stop: close the black terminal window (or press `Ctrl+C` inside it).

### macOS / Linux
1. Open the **Ollama** app from Applications (macOS) or run `ollama serve`
   (Linux). Wait for the llama icon in the menu bar.
2. Open Terminal in the `vessel-ops-ai` folder and run:
   ```
   bash scripts/start.sh
   ```
3. Open your browser to `http://localhost:8000`.
4. To stop: press `Ctrl+C` in Terminal.

---

## First-Time Install (do this with internet)

You need a one-time setup while you still have internet. Set aside 20–30
minutes for the model download (~8 GB).

### Windows
1. Install **Python 3.11+**: <https://www.python.org/downloads/windows/>
   (during install, check **"Add Python to PATH"**).
2. Install **Node.js LTS**: <https://nodejs.org/>
3. Install **Ollama**: <https://ollama.com/download/windows>
4. Download the Vessel Ops AI source: <https://github.com/switzloco/sail_pal>
   (click the green **Code** button → **Download ZIP**, then unzip).
5. Open the unzipped folder, then open the `scripts` subfolder.
   Right-click **`install.ps1`** → **Run with PowerShell**.
   (If Windows blocks it, open PowerShell and run:
   `powershell -ExecutionPolicy Bypass -File scripts\install.ps1`)
6. When it finishes, use the **Every-Day Use** instructions above.

### macOS / Linux
1. Install **Python 3.11+** (macOS: <https://www.python.org/downloads/macos/>;
   Linux: use your package manager, e.g. `sudo apt install python3 python3-venv`).
2. Install **Node.js LTS** from <https://nodejs.org/>.
3. Install **Ollama** from <https://ollama.com/download> (or on Linux:
   `curl -fsSL https://ollama.com/install.sh | sh`).
4. Open Terminal in the project folder and run:
   ```
   bash scripts/install.sh
   ```
5. When it finishes, use the **Every-Day Use** instructions above.

---

## Troubleshooting (no internet, things broke)

**The browser shows "site can't be reached":**
The server isn't running. Re-run `start.bat` (Windows) or `bash scripts/start.sh`
(Mac/Linux). Watch the terminal — it should say `Uvicorn running on
http://127.0.0.1:8000`.

**The app loads but AI replies say "Cannot switch to local: ...":**
Ollama isn't running. Open the Ollama app from your Start menu / Applications.
You should see a llama icon in your system tray / menu bar within ~10 seconds.
Then refresh the browser.

**Ollama is running but the model isn't there:**
You probably never finished `ollama pull gemma4:e2b`. You'll need internet
once to grab it (~8 GB). At sea with no internet, the AI features won't work
until you can run that pull again.

**`start.bat` says "Virtual environment not found":**
The first-time install never completed. Connect to internet and re-run
`install.ps1` (Windows) or `install.sh` (Mac/Linux).

**Where are my files?**
The database lives in `backend/data/vessel.db`. Back this up before long trips
if you've added a lot of crew, logs, or maintenance entries.

---

## Quick Reference Card (rip this off and tape it to the laptop)

```
START:   Ollama app  →  scripts\start.bat (Windows) or bash scripts/start.sh
OPEN:    http://localhost:8000
STOP:    Close the terminal window (or Ctrl+C)
MODEL:   gemma4:e2b  (run `ollama pull gemma4:e2b` once with internet)
```
