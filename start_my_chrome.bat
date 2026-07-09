@echo off
title Start MyChrome for JARVIS (deep browser automation)
echo.
echo  JARVIS deep browser control — secure CDP attach.
echo.
echo  WHY A SEPARATE PROFILE:
echo  Chrome 136+ refuses --remote-debugging-port on your normal/Default
echo  profile for security. So JARVIS drives a DEDICATED Chrome profile
echo  ("JarvisDebugProfile"). It is a real, full Chrome — you log into the
echo  sites you want JARVIS to operate (Gmail, Shopify, YouTube, etc.) ONCE
echo  in this window and those logins persist. This is the supported,
echo  sandbox-respecting method — not a security bypass.
echo.

set "JARVIS_PROFILE=%LOCALAPPDATA%\Google\Chrome\JarvisDebugProfile"
set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME%" (
  echo  [!] Could not find chrome.exe. Install Google Chrome, then retry.
  pause
  exit /b 1
)

echo  Launching JARVIS-controlled Chrome on debug port 9222...
start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%JARVIS_PROFILE%" --no-first-run --no-default-browser-check --restore-last-session

echo.
echo  Done. Keep this Chrome window OPEN.
echo  First run: log into the sites you want JARVIS to use, in THIS window.
echo  Then start JARVIS (python main.py). It will attach automatically.
timeout /t 4 >nul
