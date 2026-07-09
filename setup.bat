@echo off
echo Setting up JARVIS environment...
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\playwright install chromium
echo.
echo Setup complete. Run JARVIS with:
echo   .venv\Scripts\python main.py
