@echo off
REM ============================================================
REM  JARVIS OS - Scheduled Greetings installer
REM  Registers 4 daily Windows tasks so JARVIS greets you aloud
REM  even when the app is closed: morning (8am), midday (1pm),
REM  evening (6pm), night (10pm). Morning + midday include live
REM  weather; midday also opens your commute traffic (if set).
REM
REM  Run this ONCE (double-click). No admin needed - these are
REM  per-user tasks. To remove them later, run remove_schedule.bat
REM ============================================================
setlocal
set "DIR=%~dp0"
set "SCRIPT=%DIR%daily_greeting.py"

REM Prefer pythonw (no console window). Fall back to python.
where pythonw >nul 2>&1 && (set "PY=pythonw") || (set "PY=python")

echo Installing JARVIS daily greetings...
echo   Using: %PY%
echo   Script: %SCRIPT%
echo.

schtasks /create /tn "JARVIS Morning Greeting" /tr "%PY% \"%SCRIPT%\" morning" /sc daily /st 08:00 /f
schtasks /create /tn "JARVIS Midday Check"     /tr "%PY% \"%SCRIPT%\" midday"  /sc daily /st 13:00 /f
schtasks /create /tn "JARVIS Evening Greeting" /tr "%PY% \"%SCRIPT%\" evening" /sc daily /st 18:00 /f
schtasks /create /tn "JARVIS Night Greeting"   /tr "%PY% \"%SCRIPT%\" night"   /sc daily /st 22:00 /f
schtasks /create /tn "JARVIS Self-Care"       /tr "%PY% \"%DIR%selfcare.py\""        /sc weekly /d SUN /st 09:00 /f

echo.
echo Done. JARVIS will check in at 8:00 AM, 1:00 PM, 6:00 PM, and 10:00 PM daily.
echo Tip: set "commute_to" in config\settings.json so the 1 PM check opens your traffic.
echo (Change times in Windows Task Scheduler, or edit and re-run this file.)
echo.
echo Test it now:  python "%SCRIPT%" morning
echo.
pause
