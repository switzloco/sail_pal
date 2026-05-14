@echo off
REM Vessel Ops AI - Desktop Companion Installer (Windows)
REM
REM Double-click this file to install, or run from cmd.exe:
REM   scripts\install.bat
REM
REM This is a wrapper that runs install.ps1 with the right ExecutionPolicy
REM so Windows doesn't block the unsigned script.

setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
set RC=%ERRORLEVEL%

echo.
if %RC% NEQ 0 (
  echo Install failed with exit code %RC%. Scroll up for the error.
) else (
  echo Install complete. Next: double-click scripts\start.bat
)
echo.
pause
exit /b %RC%
