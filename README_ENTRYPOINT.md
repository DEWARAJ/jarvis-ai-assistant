# JARVIS Entry Points

## CANONICAL
```
python main.py              # dashboard (port 8765) + voice  [DEFAULT]
python main.py --terminal   # terminal mode, no browser
python main.py --port 9000  # dashboard on a custom port
python main.py --no-open    # start dashboard, don't auto-open browser
```
`main.py` and `gui.py` both launch **core/orchestrator.py** — the real JARVIS brain
(intent router, ToolRegistry, AgentRegistry, LLMClient, LiveStatus, missions, trading).

## Servers (auto-started)
- Web dashboard / HUD : http://localhost:8765  (channels/web_server.py)
- LAN remote control  : token-gated, opt-in    (channels/remote_server.py)

## DEPRECATED — do not run
- `jarvis_main.py`  — old standalone `JARVIS` class (threaded-queue). NOT used by the
  dashboard. Superseded by core/orchestrator.py.
- `agent_fabric.py` — sub-agent fabric for the deprecated jarvis_main system.
  The live system uses core/agent_registry.py instead.

## First-time setup
```
setup.bat   (Windows)   |   bash setup.sh   (Linux/Mac)
```
Installs .venv + requirements.txt (incl. anthropic, python-dotenv) + Playwright Chromium.
