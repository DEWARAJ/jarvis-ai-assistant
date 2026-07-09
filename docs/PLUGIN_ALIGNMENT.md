# JARVIS — Plugin → Implementation Alignment

This Python build of JARVIS OS is built to the spec in `plugin/jarvis-ai-os/` (the
`jarvis-ai-os.plugin` you authored). The plugin is a Claude Code / Cowork plugin
(skills + agent + hooks); this repo is the **runnable Python operating system** that
implements the same identity, rules, and behaviours. Below is exactly where each part lives.

## Skills → Code

| Plugin skill | What it specifies | Where it lives in this repo |
|---|---|---|
| `jarvis-core` | Identity, British-butler voice, forbidden/signature phrases, 3-tier permissions, NLP intent, advice mode, proactivity, memory, security | `core/orchestrator.py` → `JARVIS_PERSONA` (voice + tiers + advice + security); `core/reasoning_core.py` (NLP intent → action); `core/memory_manager.py` (persistent user model) |
| `jarvis-system-control` | File ops, app/process control, scripts, diagnostics, safety constraints | `tools/file_ops_tool.py`, `tools/windows_app_tool.py`, `tools/process_control.py`, `tools/system_command.py`, `tools/system_info_tool.py`, `tools/input_control.py`, `tools/power_control.py` |
| `jarvis-research` | Senior-analyst research, source triangulation, A/B/C confidence, synthesis | `agents/ultron_agent.py` (`ULTRON_SYSTEM`) + `tools/web_tool.py` + `core/orchestrator.py` `_research` |
| `jarvis-task-automation` | Multi-step orchestration, plan→execute→deliver, workflow templates | `core/orchestrator.py` `_autonomous`, `_daily_briefing`; `tools/automation_tool.py`; `daily_greeting.py` + `setup_schedule.bat` (scheduled workflows) |
| `jarvis-selfimprovement` | Learn from corrections, track preferences, adapt | `core/memory_manager.py` (`remember`, preferences), persona self-improvement clause, `memory/` store |

## Agent → Code

| Plugin agent | Role | Implementation |
|---|---|---|
| `jarvis-autonomous-agent` | Large, open-ended tasks end-to-end, pause only at Tier-2 | `core/orchestrator.py` `_autonomous()` + `_AUTONOMOUS_SYSTEM`; triggered by "handle this end to end", "just get it done", "take it from here". ULTRON (`agents/ultron_agent.py`) is the research/strategy brain it leans on. |

## Hooks → Code

The plugin's hooks are session-level prompts for Claude Code. In this Python OS the same
intent is enforced in the pipeline (`Orchestrator.handle` → classify → safety → dispatch):

| Plugin hook | Event | Python equivalent |
|---|---|---|
| Session initialiser | `SessionStart` | Boot banner + situational scan (`_situation()`), time-greeting (`_time_greeting`), dashboard `checkGreeting()` |
| Execution guard | `PreToolUse` | `core/safety_guard.py` `review()` — runs before any risky action; 3-tier gate |
| Intent parser | `UserPromptSubmit` | `core/reasoning_core.py` `classify()` + `safety_guard._detect_injection()` |
| Quality check | `Stop` | Honest-reporting persona clause + self-improvement memory writes |

## Permission Framework (3 tiers)

The plugin's tiers map onto the existing, test-covered safety mechanism:

| Plugin tier | Meaning | Mechanism (`config/permissions.json` + `safety_guard.py`) |
|---|---|---|
| **Tier 1 — Full autonomy** | read / observe / analyse / research / draft | `allowed` → acts immediately |
| **Tier 2 — Confirm first** | write / modify / send / execute / delete | `requires_confirmation` → described, held for "go ahead" |
| **Tier 3 — Explicit authorisation** | irreversible / financial / wide-scope / third-party | `tier3_explicit` subset of confirm (delete, overwrite, spend, trade, shutdown, restart) → demands a clear, specific "yes, do it"; plus `forbidden_unless_enabled` for autonomous/abuse classes |

Security protocols (`plugin/.../security-protocols.md`) are enforced by `safety_guard.py`:
injection detection (Layer 0), forbidden block (Layer 1), confirm hold (Layer 2), audit log
(`logs/audit.log`), threat scoring. Credentials/keys are never stored (`memory_manager` refuses secrets; keys read from `.env` only).

## Using the plugin itself (optional)

The bundled plugin in `plugin/jarvis-ai-os/` can also be installed on the Claude/Cowork side
via Settings → Capabilities, to give Claude the same identity in chat. The Python OS here is
the standalone runnable system — `python main.py`.
