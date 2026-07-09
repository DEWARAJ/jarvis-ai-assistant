@echo off
REM ============================================================
REM  JARVIS OS - remove the scheduled daily greetings.
REM ============================================================
echo Removing JARVIS daily greetings...
schtasks /delete /tn "JARVIS Morning Greeting" /f
schtasks /delete /tn "JARVIS Midday Check"     /f
schtasks /delete /tn "JARVIS Evening Greeting" /f
schtasks /delete /tn "JARVIS Night Greeting"   /f
schtasks /delete /tn "JARVIS Self-Care"       /f
echo.
echo Removed. JARVIS will no longer greet you automatically.
pause
