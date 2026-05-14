@echo off
REM Vessel Ops AI — Start Server (Windows)
REM
REM Double-click this file to launch the local server, or run from cmd.exe:
REM   scripts\start.bat
REM
REM Once it says "Uvicorn running", open http://localhost:8000 in your browser.

setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo ERROR: Virtual environment not found.
  echo Double-click scripts\install.bat first to set up the desktop companion.
  echo.
  pause
  exit /b 1
)

echo Checking Ollama...
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:11434/api/tags' -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  echo.
  echo WARNING: Ollama isn't running. Open the Ollama app from your Start menu,
  echo wait until you see its icon in the system tray, then run this script again.
  echo.
  pause
  exit /b 1
)

echo.
echo ====================================================
echo   Vessel Ops AI — starting on http://localhost:8000
echo   Press Ctrl+C to stop.
echo ====================================================
echo.

REM Open the browser after a short delay
start "" /min powershell -NoProfile -Command "Start-Sleep -Seconds 3; Start-Process 'http://localhost:8000'"

REM Run the server in the foreground
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
