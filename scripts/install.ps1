# Vessel Ops AI — Desktop Companion Installer (Windows)
#
# HOW TO RUN THIS:
#   1. Open the scripts folder in File Explorer
#   2. Click the address bar at the top, type "powershell", press Enter
#   3. In the PowerShell window that opens, type:
#         powershell -ExecutionPolicy Bypass -File install.ps1
#      and press Enter.
#
#   If Windows shows a blue "SmartScreen" warning, click "More info" -> "Run anyway".
#
# After this finishes, double-click start.bat to launch the app.

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $RepoRoot

function Info($msg)  { Write-Host "▶ $msg" -ForegroundColor Green }
function Warn($msg)  { Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Fail($msg)  { Write-Host "✗ $msg" -ForegroundColor Red; exit 1 }

$Model = "gemma4:e2b"

# ── Python ────────────────────────────────────────────────────────────────────
Info "Checking Python..."
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  Fail "Python is not installed. Install Python 3.11+ from https://www.python.org/downloads/windows/ (check 'Add Python to PATH'), then re-run."
}

# Detect Microsoft Store stub (opens the Store instead of running Python)
$pythonPath = $pythonCmd.Source
if ($pythonPath -match "WindowsApps" -or $pythonPath -match "Microsoft\\WindowsApps") {
  Fail "The 'python' command points to the Microsoft Store stub, not a real Python install.`nPlease install Python 3.11+ from https://www.python.org/downloads/windows/ (check 'Add Python to PATH'), then re-run."
}

$pyVerLine = & python --version 2>&1
if ($pyVerLine -notmatch "Python (\d+)\.(\d+)") {
  Fail "Could not parse Python version: $pyVerLine"
}
$pyMajor = [int]$Matches[1]; $pyMinor = [int]$Matches[2]
if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 11)) {
  Fail "Python $pyMajor.$pyMinor is too old. Install 3.11+ from https://www.python.org/downloads/windows/."
}
Info "Python $pyMajor.$pyMinor ✓"

# ── Node.js ───────────────────────────────────────────────────────────────────
Info "Checking Node.js..."
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
  Fail "Node.js is not installed. Install LTS (20+) from https://nodejs.org/, then re-run."
}
$nodeVer = (& node -v).Trim().TrimStart('v')
$nodeMajor = [int]($nodeVer.Split('.')[0])
if ($nodeMajor -lt 20) {
  Fail "Node.js v$nodeMajor is too old. Install LTS (20+) from https://nodejs.org/."
}
Info "Node.js v$nodeMajor ✓"

# ── Ollama ────────────────────────────────────────────────────────────────────
Info "Checking Ollama..."
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCmd) {
  Warn "Ollama not found."
  Warn "  1. Download and install from: https://ollama.com/download/windows"
  Warn "  2. Open the Ollama app — wait for the llama icon in your system tray (bottom-right)"
  Warn "  3. Re-run this script"
  Start-Process "https://ollama.com/download/windows"
  Fail "Ollama install required."
}
Info "Ollama detected ✓"

# ── Python venv + backend deps ───────────────────────────────────────────────
if (-not (Test-Path ".venv")) {
  Info "Creating Python virtual environment..."
  & python -m venv .venv
}
$venvPython = "$RepoRoot\.venv\Scripts\python.exe"
Info "Installing backend dependencies..."
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet -r backend\requirements.txt

# ── Verify Ollama is running ─────────────────────────────────────────────────
Info "Ensuring Ollama is running..."
try {
  Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
} catch {
  Warn "Ollama is installed but not running."
  Warn "  -> Open the Ollama app from your Start menu"
  Warn "  -> Wait for the llama icon in your system tray (bottom-right corner)"
  Warn "  -> Then re-run this script"
  Fail "Ollama not running."
}

# ── Pull model ────────────────────────────────────────────────────────────────
$tags = & ollama list 2>$null
if ($tags -match [regex]::Escape($Model.Split(':')[0])) {
  Info "Model $Model already pulled ✓"
} else {
  Info "Pulling $Model (~8 GB, one-time download — this may take 15-30 minutes)..."
  Info "If interrupted, just re-run this script — Ollama resumes from where it left off."
  & ollama pull $Model
}

# ── Frontend build ───────────────────────────────────────────────────────────
if (-not (Test-Path "frontend_out\index.html")) {
  Info "Building frontend (one-time)..."
  Push-Location frontend
  & npm ci --silent
  $env:NEXT_PUBLIC_API_BASE = ""
  $env:WEB_EXPORT = "1"
  & npm run build --silent
  Pop-Location
  if (-not (Test-Path "frontend\out\index.html")) {
    Fail "Frontend build failed — index.html not found. Check Node.js version (need 20+) and try again."
  }
  Copy-Item -Recurse -Force frontend\out frontend_out
  Info "Frontend built ✓"
} else {
  Info "Frontend already built ✓"
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  Install complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  Next step:  double-click  scripts\start.bat"
Write-Host "  Then open:  http://localhost:8000"
Write-Host ""

# ── Drop an offline-ready quickstart on the Desktop ──────────────────────────
$desktop = [Environment]::GetFolderPath("Desktop")
if ((Test-Path $desktop) -and (Test-Path "DESKTOP_QUICKSTART.md")) {
  Copy-Item -Force "DESKTOP_QUICKSTART.md" "$desktop\Vessel-Ops-Quickstart.md"
  Info "Saved offline instructions to: $desktop\Vessel-Ops-Quickstart.md"
  Warn "IMPORTANT: Keep this file — you'll need it if you lose internet at sea."
}
