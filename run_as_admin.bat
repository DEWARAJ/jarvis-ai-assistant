@echo off
title JARVIS OS (Administrator)
:: ── Auto-elevate: if not already admin, relaunch this file as admin (UAC prompt) ──
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator permission...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
:: ── Now running as admin ──
cd /d "%~dp0"
echo Running JARVIS OS as administrator...
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" gui.py
) else (
    python gui.py
)
pause
