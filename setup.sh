#!/bin/bash
echo "Setting up JARVIS environment..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
echo ""
echo "Setup complete. Run JARVIS with:"
echo "  .venv/bin/python main.py"
