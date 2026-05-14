# Vessel Ops AI - Desktop Companion Installer (Windows)
#
# HOW TO RUN THIS:
#   Easiest: in File Explorer, double-click "install.bat" in this folder.
#   That wrapper invokes this script with the right flags.
#
#   Manual fallback: open cmd in the scripts folder and run:
#         powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
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

# Resolve a real Python interpreter, avoiding the MS Store stub at
# %LOCALAPPDATA%\Microsoft\WindowsApps\python.exe. Strategy:
#   1. Prefer the py launcher (installed by python.org installer; bypasses the stub).
#   2. Otherwise scan every python/python3 on PATH and pick the first non-WindowsApps one.
$pythonExe = $null

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
  $verLine = & py -3 --version 2>&1
  if ($LASTEXITCODE -eq 0 -and $verLine -match "Python (\d+)\.(\d+)") {
    $pythonExe = @("py", "-3")
  }
}

if (-not $pythonExe) {
  $candidates = @()
  $candidates += Get-Command python  -All -ErrorAction SilentlyContinue
  $candidates += Get-Command python3 -All -ErrorAction SilentlyContinue
  foreach ($c in $candidates) {
    if ($c.Source -notmatch "WindowsApps") {
      $pythonExe = @($c.Source)
      break
    }
  }
}

if (-not $pythonExe) {
  Fail @"
No real Python interpreter found. The 'python' command on this PATH points to
the Microsoft Store stub (or nothing at all).

Fix one of these and re-run install.bat:
  A) Install Python 3.11+ from https://www.python.org/downloads/windows/
     and check 'Add Python to PATH' during install.
  B) If you've already installed it, disable the Store stub:
     Settings -> Apps -> Advanced app settings -> App execution aliases ->
     turn OFF 'App Installer  python.exe' and 'App Installer  python3.exe'.
"@
}

$pyVerLine = & $pythonExe[0] $pythonExe[1..($pythonExe.Length-1)] --version 2>&1
if ($pyVerLine -notmatch "Python (\d+)\.(\d+)") {
  Fail "Could not parse Python version: $pyVerLine"
}
$pyMajor = [int]$Matches[1]; $pyMinor = [int]$Matches[2]
if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 11)) {
  Fail "Python $pyMajor.$pyMinor is too old. Install 3.11+ from https://www.python.org/downloads/windows/."
}

# Warn about very-new Python where ML deps may not have Windows wheels yet.
# If pip can't find wheels for chromadb / sentence-transformers / pymupdf on
# this version, it falls back to source builds which need a C++ toolchain
# the user almost certainly doesn't have.
if ($pyMajor -eq 3 -and $pyMinor -ge 13) {
  Warn "Python $pyMajor.$pyMinor is newer than what some dependencies"
  Warn "(chromadb, sentence-transformers, pymupdf) currently ship Windows wheels for."
  Warn "If pip install fails below, install Python 3.11 or 3.12 from"
  Warn "https://www.python.org/downloads/windows/ and re-run install.bat."
  Warn "(The 'py' launcher will pick the newest installed Python by default;"
  Warn " we'll try 'py -3.12' first if it exists.)"

  # Prefer an older interpreter if the user has one installed alongside.
  foreach ($preferred in @("3.12","3.11")) {
    $check = & py "-$preferred" --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $check -match "Python (\d+)\.(\d+)") {
      $pythonExe = @("py", "-$preferred")
      $pyMajor = [int]$Matches[1]; $pyMinor = [int]$Matches[2]
      Info "Switched to Python $pyMajor.$pyMinor via 'py -$preferred'"
      break
    }
  }
}

Info "Python $pyMajor.$pyMinor ($($pythonExe -join ' ')) ✓"

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
  & $pythonExe[0] $pythonExe[1..($pythonExe.Length-1)] -m venv .venv
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
