# JARVIS OS

A serious, modular personal AI operating system and business command center.
Not a chatbot — a command brain with sub-agents, memory, safety gates, and permission control.

## Status: Phase 1 (Terminal Core)

Runnable today. No external APIs connected. Pure Python standard library.

## Quick start

```powershell
cd jarvis-os
python main.py
```

You should see:

```
JARVIS OS ONLINE
```

Type `help` to see commands, `shutdown jarvis` to exit.




## Action commands (live agent)

```
open chrome | open calculator | open notepad | open downloads | open settings
google best ai tools for ecommerce
search youtube for shopify product page tips
amazon wireless earbuds
open website https://www.google.com
latest ai news | latest crypto news | daily briefing
research best ai agents in 2026
fast mode | deep mode | private mode | show status
organize downloads   (preview, then 'confirm')
```

Setup for full power:

```powershell
cd C:\\Users\\dewar\\Documents\\Claude\\Projects\\JARVIS
python -m pip install -r requirements.txt
python gui.py
python -m pytest
```

App-launch verification uses `psutil` (in requirements). Browser commands open real
search URLs in your default browser — no extra install. Optional deep browser automation
(Playwright) is documented but not required.

## Live dashboard + voice

Launch the Iron-Man-style dashboard with voice:

```powershell
python gui.py
```

It opens in your browser (use **Chrome or Edge** for voice). Click the mic and speak, or type. Toggle spoken replies with the VOICE button (bottom-right). The dashboard uses the same brain, agents, and safety as terminal mode.

## Make JARVIS think (LLM)

JARVIS uses a local LLM via **Ollama** by default — free, private, no API key.

1. Install Ollama (https://ollama.com) and pull a model:

   ```powershell
   ollama run llama3.2
   ```

2. Start JARVIS (`python main.py`) and check the brain:

   ```
   JARVIS> llm status
   ```

3. Ask anything, or use `think <question>`. Commands like `business review`,
   `ad hooks`, and `draft customer reply` now use the model too.

To use NVIDIA NIM instead (cloud, free tier): in `config/settings.json` set
`llm.provider` to `openai`, `base_url` to `https://integrate.api.nvidia.com/v1`,
`model` to e.g. `meta/llama-3.1-8b-instruct`, and `api_key_env` to `NVIDIA_API_KEY`,
then put `NVIDIA_API_KEY=nvapi-...` in a `.env` file (never in config or memory).

## Architecture

- **Orchestrator** (`core/orchestrator.py`) — the command brain. Observe → Orient → Decide → Act (OODA). Routes every request through Safety Guard + Permission Manager before acting.
- **Reasoning Core** (`core/reasoning_core.py`) — intent classification + task decomposition.
- **Agent Registry** (`core/agent_registry.py`) — 14 specialist sub-agents, each scoped.
- **Tool Registry** (`core/tool_registry.py`) — modular safe tools.
- **Permission Manager** (`core/permission_manager.py`) — allowed / requires-confirmation / forbidden tiers.
- **Safety Guard** (`core/safety_guard.py`) — blocks risky/irreversible actions until approved.
- **Memory Manager** (`core/memory_manager.py`) — structured local JSON memory; never stores secrets.
- **Task Manager** (`core/task_manager.py`) — task list with persistence.

## Safety promises

JARVIS will never (without explicit Master permission): delete/overwrite files, spend money,
send messages, post online, run risky commands, connect external APIs, or place trades.
See `SAFETY_PROTOCOL.md`, `MASTER_PERMISSIONS.md`, `LOYALTY_PROTOCOL.md`.

## Phases

1. Terminal core (DONE) — orchestrator, agents, memory, safety, permissions, tasks.
2. Business / e-commerce / support / marketing depth.
3. Trading research & journal.
4. Automation engine.
5. Voice output + optional input.
6. GUI dashboard.
7. Tests & hardening.
8. External integrations (only after approval).

See `PROJECT_STATE.md` and `TODO.md` for live status.
