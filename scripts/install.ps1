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

# Resolve a real Python interpreter by probing behavior, not by checking paths.
# Modern Windows complicates this:
#   - Old MS Store stub: python.exe under WindowsApps that opens the Store.
#   - New Python Install Manager (pymanager): python.exe under WindowsApps that
#     IS a real interpreter routed through pymanager. Same path, opposite truth.
# So we just run --version on each candidate and accept the first one that
# returns a parseable "Python X.Y".

function Try-Python {
  param([string[]]$Cmd)
  try {
    $out = & $Cmd[0] $Cmd[1..($Cmd.Length-1)] --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $out -match "Python (\d+)\.(\d+)") {
      return @{ Cmd = $Cmd; Major = [int]$Matches[1]; Minor = [int]$Matches[2] }
    }
  } catch { }
  return $null
}

$pythonExe = $null
$pyMajor = 0; $pyMinor = 0

# Try in order of preference. py -3 first (works for python.org and pymanager
# installs), then bare commands, then explicit python3.
$probeList = @(
  @("py","-3"),
  @("python"),
  @("python3")
)

# Also probe every python/python3 on PATH in case the first match is a broken
# stub but a later one works.
foreach ($name in @("python","python3")) {
  $all = Get-Command $name -All -ErrorAction SilentlyContinue
  foreach ($c in $all) { $probeList += ,@($c.Source) }
}

foreach ($cmd in $probeList) {
  $r = Try-Python -Cmd $cmd
  if ($r) {
    $pythonExe = $r.Cmd; $pyMajor = $r.Major; $pyMinor = $r.Minor
    break
  }
}

if (-not $pythonExe) {
  Fail @"
No working Python interpreter found.

Install Python 3.11+ from https://www.python.org/downloads/windows/ (check
'Add Python to PATH' during install), then re-run install.bat.

If you're using the new Python Install Manager (pymanager) and 'python' still
doesn't work, open:
  Settings -> Apps -> Advanced app settings -> App execution aliases
and make sure 'py.exe' or 'python.exe' under 'Python install manager' is ON.
"@
}
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
