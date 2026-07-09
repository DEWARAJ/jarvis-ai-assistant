# JARVIS OS — Project State
_Last updated: 2026-06-09_

## Status: PHASE 1 COMPLETE ✅

## Architecture
```
main.py → Orchestrator → ReasoningCore (intent) → SafetyGuard → Tool dispatch
```

## Core Components

| Component | File | Status |
|---|---|---|
| Entry point | `main.py` | ✅ |
| Orchestrator | `core/orchestrator.py` | ✅ |
| Reasoning / intent | `core/reasoning_core.py` | ✅ 70+ rules |
| Safety guard | `core/safety_guard.py` | ✅ hardened |
| Permission manager | `core/permission_manager.py` | ✅ |
| LLM client | `core/llm_client.py` | ✅ |
| Memory manager | `core/memory_manager.py` | ✅ |
| Tool registry | `core/tool_registry.py` | ✅ |
| Logger | `core/logger.py` | ✅ |

## Tools (config/tools.json)

| Tool | Scope | Status |
|---|---|---|
| youtube | Media playback — next/prev/stop/seek/fullscreen | ✅ |
| volume | System volume (pycaw exact + VK fallback) | ✅ |
| system_info | CPU/RAM/disk/battery/network diagnostics | ✅ NEW |
| browser | Open sites, search | ✅ |
| web | Fetch public pages | ✅ |
| file / file_ops | Project & user files | ✅ |
| notes | notes/ directory | ✅ |
| task | memory/tasks.json | ✅ |
| windows_app | Whitelisted launcher | ✅ |
| business | business_knowledge/ | ✅ |
| customer_support | Draft responses | ✅ |
| ecommerce | Audit & copy | ✅ |
| trading | Journal & risk | ✅ |
| automation | Plan generation | ✅ |
| power | Shutdown/restart/sleep | ✅ |
| screen | Screenshots | ✅ |
| input | Keyboard & mouse | ✅ |
| process | Close/kill apps | ✅ |
| network | WiFi/Bluetooth | ✅ |
| email | Read-only inbox | ✅ |
| news | Live RSS | ✅ |
| browser_root | Playwright execution root | ✅ |
| weather | wttr.in live conditions (no key) | ✅ |

## Companion Layer (NEW)

| Feature | Where | Status |
|---|---|---|
| Time-aware greetings (morning/afternoon/evening/night) | `core/orchestrator._time_greeting` + `/api/greeting` | ✅ |
| Auto-greeting in dashboard (once per slot) | `ui/dashboard.html checkGreeting()` | ✅ |
| Clap-to-wake | `ui/dashboard.html onClap()` (Web Audio) | ✅ |
| Weather on demand | `weather` / `weather in <city>` | ✅ |
| Traffic on demand | `traffic to <place>` → live Google Maps | ✅ |
| **Scheduled greetings when app is CLOSED** | `daily_greeting.py` + `setup_schedule.bat` | ✅ NEW |

### Scheduled greetings (OS-level)
- `daily_greeting.py morning|midday|evening|night` — standalone, speaks aloud via Windows SAPI (no GUI). Morning + midday include live weather; midday also opens live Google Maps traffic for your commute (Chrome-preferred) when `companion.commute_to` is set in settings.json. Degrades silently off-Windows / offline.
- `setup_schedule.bat` — registers 4 per-user Windows Task Scheduler jobs (08:00 / 13:00 / 18:00 / 22:00 daily). No admin required.
- `remove_schedule.bat` — deletes them.
- Commute config: `config/settings.json → companion.commute_to` (and optional `commute_from`). Blank = weather only.

## ULTRON — Advanced Advisor Sub-Agent (NEW)

ULTRON is JARVIS's deep research-and-strategy brain. The butler delegates hard thinking to it; ULTRON pulls **live web references**, reasons, and advises — but **advises only, never executes** (bound by the same SafetyGuard; loyal, no autonomous action).

| Aspect | Detail |
|---|---|
| File | `agents/ultron_agent.py` (class `UltronAgent`) |
| Registered | `config/agents.json → "ultron"` (risk: low) |
| Tools used | `web` (DuckDuckGo search + page fetch) + LLM synthesis with source citation |
| Actions | `research`, `advise`, `improve`, `deep_think`, `check_in` |
| Voice | Own crisp analyst persona (`ULTRON_SYSTEM`), spoken-friendly, cites best source |
| Fallbacks | No LLM → returns raw web findings; no web → advises from own expertise and says so; neither → honest "couldn't reach" |

### Commands (routed in `core/reasoning_core.py`, handled in `core/orchestrator.py`)
- `advise me on <task>` / `how do I <X>` / `how to <X>` / `best way to <X>` / `tips for <X>` → ULTRON advice (web-referenced)
- `how can I improve <X>` / `optimize <X>` → ULTRON improvements (3 ranked upgrades + trade-offs)
- `what should I do next` / `check in` / `any suggestions` → proactive butler check-in (highest-leverage next step + a sharp question)
- `ultron <anything>` → direct line (auto-routes to research / advise / improve / deep analysis)
- `research <topic>` → now delegates to ULTRON (Perplexity fast-path first if its key is set)
- Daily briefing now ends by proactively offering ULTRON.

> Proactivity: ULTRON's `check_in` both advises and **asks** the master a focusing question — the butler "asks for things" rather than only answering.

## Built to the `jarvis-ai-os` Plugin Spec (NEW)

The project now implements the JARVIS plugin you authored (bundled at `plugin/jarvis-ai-os/`). Full mapping in `docs/PLUGIN_ALIGNMENT.md`.

| Plugin component | Implemented as |
|---|---|
| `jarvis-core` identity & voice | Rewritten `JARVIS_PERSONA` — "Just A Rather Very Intelligent System", British butler, signature + **forbidden** phrases, "sir", advice mode, proactivity, security |
| 3-tier permission framework | `config/permissions.json` (`tier3_explicit` added) + `safety_guard.py`; presented in `show permissions` / `status` as Tier 1 (autonomy) / Tier 2 (confirm) / Tier 3 (explicit) |
| `jarvis-research` methodology | `ULTRON_SYSTEM` — senior-analyst, source triangulation, A/B/C confidence, synthesis over links |
| `jarvis-task-automation` + `jarvis-autonomous-agent` | `_autonomous()` + `_AUTONOMOUS_ADDENDUM` — "handle this end to end / just get it done / take care of it" → plan, do Tier-1, pause at Tier-2 |
| `jarvis-selfimprovement` | `memory_manager` (remember/preferences, refuses secrets) + persona self-improvement clause |
| Hooks (SessionStart/PreToolUse/UserPromptSubmit/Stop) | boot scan + `_situation()`; `safety_guard.review()`; `reasoning_core.classify()` + injection detection; honest-report persona |
| `what's the situation` / `sitrep` | `_situation()` — crisp state report (tasks, brain, pending, last action) |

New commands: `handle <task> end to end` · `just get it done` · `take care of it` · `what's the situation` · `sitrep`. Tests: 39/39 passing.

> The bundled plugin can also be installed Claude-side (Settings → Capabilities) to give Claude the same identity in chat; this repo is the runnable Python OS.

## LLM Tool-Calling Brain — "Agentic Core" (NEW, biggest upgrade)

JARVIS no longer relies on keyword matching alone. Anything the rule-based core doesn't catch now flows to an **LLM brain that understands intent and chooses + runs real actions**.

| Aspect | Detail |
|---|---|
| File | `core/agentic_core.py` (`AgenticCore`, `CATALOG`) |
| How it works | LLM returns strict JSON `{say, steps:[{action,arg}]}`; orchestrator runs each step via `_run_action` → `_dispatch` (reusing every handler) |
| Catalog | ~38 actions mapped to real intents (open/search/play, scroll, volume, screen, news, weather, price, research, advise, tasks, memory, wifi/bt, code, terminal, power…) |
| Chaining | Multi-step in one request (e.g. "pull up the weather in Tokyo in Chrome" → open_app + browser_google), capped at 4 steps |
| Safety | Every step passes through the SafetyGuard + 3-tier gate; a brain-planned delete/power/terminal action is **held for confirmation, never auto-run** (test-verified) |
| Robustness | Invalid JSON → treated as a spoken answer; offline/no-LLM → graceful fallback; recursion-guarded (`_in_agentic`) |
| Toggle | `config/settings.json → llm.agentic` (default true) |
| Flow | rule-based fast-path first (instant, deterministic) → brain catches everything else, so it understands paraphrases, not just exact phrases |

This is the change that moves JARVIS from "matches ~100 phrases" to "understands what you mean and acts." Tests: **44/44 passing** (5 new: JSON parse, action chaining, pure chat, safety-hold, offline).

## Reliability — Self-Verifying Actions + Doctor (NEW, Upgrade 2 of 6)

Makes JARVIS trustworthy day-to-day: it checks that actions actually worked, retries safe ones, and never fakes success.

| Aspect | Detail |
|---|---|
| File | `core/reliability.py` (`attempt`, `looks_failed`, `log_action`, `RETRIABLE_ACTIONS`) |
| Self-verify + retry | `_run_action` checks each result for failure markers; **read-only** actions (research, news, weather, price, briefings…) auto-retry once on a transient failure; side-effecting actions (open, volume, delete) run **once** and are verified — never blind-retried |
| Honest failure | A failed action's real reason is preserved and reported; never turned into fake success |
| Action log | Every action outcome (ok/attempts/snippet) appended to `logs/actions.log` |
| `doctor` command | Full live self-diagnostic: OS, admin, optional libs present/missing, API keys (set/missing — values never shown), internet + brain reachability, tools/agents counts, pending action, and a clear verdict |

Commands: `doctor` · `health check` · `full check`. Tests: **48/48 passing** (4 new: retry+markers, read-only retry, no-blind-retry on side effects, doctor).

## Never Go Dumb — Multi-Brain Failover (NEW, Upgrade 3 of 6)

JARVIS now always has a working mind. `LLMClient.chat()` is resilient, so every caller (orchestrator, ULTRON, agentic brain, research) benefits automatically.

| Aspect | Detail |
|---|---|
| Failover chain | Tries the active brain, then auto-fails-over through the other usable brains; **local Ollama is the floor** so it works even fully offline |
| Health-aware | A brain that fails is marked dead for a cooldown (`llm.fallback_cooldown`, 60s) and skipped — no wasting time on a known-down provider |
| Key-aware | Brains whose API key isn't set are skipped automatically (never tried-and-failed) |
| Transparent | `self.last_brain` / `self.last_failover` track which brain actually answered; shown in `status` and `doctor` |
| Config | `config/settings.json → llm.fallback` (default `["claude","nvidia","ollama"]`) |
| Honest | If every brain is down, returns nothing and JARVIS falls back to its rule-based reply — never fakes it |

This means: cloud key + internet → best quality (Claude); internet only / different key → next cloud; no internet but Ollama installed → still smart, locally. Tests: **52/52 passing** (4 new: failover, local floor, key-skip, no-failover-when-healthy).

## Real Senses — Vision Loop + Wake Word + Voice (NEW, Upgrade 4 of 6)

JARVIS can now look at the screen, act, and **look again to verify** — and the agentic brain can choose to use its eyes mid-task.

| Aspect | Detail |
|---|---|
| File | `core/vision_core.py` (`VisionCore.capture / look / verify`) |
| Look | `see my screen`, `what's on my screen` → captures + Claude vision describes it |
| Verify (act→look→verify) | `verify <X>` (e.g. "verify the video is playing") → captures, judges YES/NO with a reason; honest "couldn't be certain" when unsure |
| Brain-driven eyes | `see_screen` + `verify_screen` are agentic actions, so the brain can plan `[youtube_play X, verify_screen "the video is playing"]` — it confirms its own work visually |
| Graceful | No capture lib → "couldn't capture (pip install pillow)"; no `ANTHROPIC_API_KEY` → says it needs eyes; never fakes a result |
| Wake word | Dashboard mic (when ON) only acts when addressed: say "**Jarvis** …", then it strips the wake word (`voice.wake_word`, default "jarvis"); just "Jarvis" → "Yes, sir?" |
| Voice | Calmer butler cadence (rate 0.97, pitch 1.0) on the preferred British voice |

Vision is Claude-only (needs `ANTHROPIC_API_KEY` + `pillow`). Tests: **56/56 passing** (4 new: look+verify, graceful-no-capture, verify intent/handler, catalog has eyes).

## Proactive Autonomy — Background Monitoring (NEW, Upgrade 5 of 6)

JARVIS now watches things on its own and surfaces alerts before you ask — read-only (Tier 1), no actions.

| Aspect | Detail |
|---|---|
| Engine | `core/watch_manager.py` — price / system / news / url watchers, thresholds + change-detection, cooldown, persistence (`memory/watches.json`), injected data providers |
| Background loop | `Orchestrator.start_monitor()` (daemon thread, opt-in via `proactive.enabled`, every `interval_seconds`) → checks watches → buffers alerts; started by the web server |
| Delivery | `/api/alerts` endpoint drains alerts; dashboard polls every 30s and surfaces + speaks them; terminal: `anything new` |
| Commands | `monitor btc below 50000` · `alert me if battery drops below 20` · `monitor disk` · `watch news about AI` · `watch the page <url>` · `show monitors` · `stop monitoring <id>` · `anything new` |
| Kinds | **price** (cross threshold or ±% move), **system** (cpu/memory/disk/battery), **news** (new top headline on a topic), **url** (page content changed) |
| Safe + tidy | Watchers only read; cooldown prevents alert spam; bare `watch`/`watchlist` still = the trading watchlist (no collision) |

Tests: **63/63 passing** (7 new: CRUD+persistence, price/system fire, no-fire, news arm→fire, cooldown, command routing/parse, drain).

## Depth over Breadth — Workflow Engine (NEW, Upgrade 6 of 6)

The few things you do daily, run end-to-end as robust multi-step routines that tie the whole system together.

| Aspect | Detail |
|---|---|
| Engine | `core/workflows.py` (`WorkflowEngine._run_steps`) — per-step live status, retry on safe network calls, **honest partial delivery** (a failed optional step is labelled, the rest still delivered; a critical failure aborts and says so) |
| `start my day` | greeting → live weather → top headlines → open tasks → ULTRON/LLM focus → pending monitor alerts, composed into one briefing |
| `wind down` / `end my day` | completed count → still-open for tomorrow → alerts → good-night |
| `focus on <task>` | locks onto a task (or your top one), gives a one-line plan + first action |
| `research brief on <topic>` | ULTRON deep research → **saves a `.md` brief** to `briefs/` → returns the path + preview (honest if it couldn't gather or save) |
| Brain-callable | `wf_start_day` + `wf_research_brief` are in the agentic catalog |

Tests: **68/68 passing** (5 new: engine partial+critical, start-day compose, focus arg, brief saves file, routing).

---

## Road to 9/10 — COMPLETE ✅ (all 6 upgrades)

1. **LLM tool-calling brain** — understands intent, chooses + runs actions, chains steps
2. **Reliability** — self-verifying actions, honest retry, action log, `doctor`
3. **Never go dumb** — multi-brain failover (cloud → local Ollama floor)
4. **Real senses** — screen vision look→verify loop, wake word, calmer voice
5. **Proactive autonomy** — background monitoring + alerts surfaced on their own
6. **Depth over breadth** — bulletproof daily workflows

68/68 tests passing. The honest cap remains: a literal flawless sci-fi JARVIS isn't possible; this is the strong, real-world ~9/10 version — and every piece degrades honestly rather than faking success.

## Toward Frontier-Agent Behaviour — ReAct Loop + Vision Control (NEW)

The two capabilities that separate a smart assistant from a frontier "computer-use" agent.

| Aspect | Detail |
|---|---|
| ReAct loop | `agentic_core.act_loop` — true observe→think→act→observe→self-correct, one action per turn, fed prior observations, bounded to 6 steps, ends with a summary + transcript. `handle this end to end` / `just get it done` / `agent <goal>` now run this loop |
| Vision-grounded clicking | `vision_core.locate(target)` → Claude vision returns the element's centre (% of screen) → mapped to pixels via `pyautogui.size()` → `click_at`. Command `click the <X>` / catalog action `click_vision`, so the loop can *see a button and click it* |
| Safety preserved | Every loop step runs through `_run_action` → `_dispatch` → SafetyGuard; risky steps still held for confirmation; invalid actions skipped |
| Honest | No `pyautogui`/vision key → says so; can't locate → says so; step limit → reports the transcript; never fakes a click |

Tests: **76/76 passing** (8 new: loop executes/finishes, skips invalid, offline, autonomous-uses-loop, vision click locate+click, not-found, locate degrades, routing+catalog).

### Masterpiece grounding (UIA + two-pass vision)

`vision_core.locate` is now layered, best-first — the same technique frontier Windows "operator" agents use:

1. **Accessibility tree (UIA)** — if `uiautomation` is installed, find the control by name in the foreground window and click its exact centre. Pixel-perfect, no guessing.
2. **Two-pass vision ("zoom and confirm")** — coarse locate on the full screen → crop a window around it and 2× upscale → re-locate precisely within the crop → map back to absolute pixels. Far more accurate than a single estimate on dense UIs.
3. **Single-pass vision** — fallback when zoom can't refine.

`_click_vision` reports which method grounded the click. Degrades honestly at every layer (no `uiautomation` → vision; no `pillow`/vision key → says so). Config: `vision.two_pass`. Pure mapping math (`refine_point`) is unit-tested.

Tests: **80/80 passing** (12 new across the ReAct loop, vision click, and layered grounding).

> Honest scope: clicking is now *near frontier-grade* — UIA is exact, two-pass vision is strong on real UIs. The remaining gap to lab agents is long-horizon planning (loop capped at 6 steps), eval scale, and that the reasoning is a borrowed frontier model rather than a bespoke one. So: **acting ≈ near-lab; overall a strong agent, not a literal frontier lab system.**

## Long-Horizon Planner + Episodic Memory (NEW)

Closes most of the *planning* gap and makes JARVIS get better with use.

| Aspect | Detail |
|---|---|
| Planner | `core/planner.py` — decomposes a big goal into 2–6 ordered subgoals, runs each through the ReAct `act_loop`, **verifies each, makes one repair attempt on failure**, then reports done/blocked per subgoal. Goes well beyond the 6-step single-loop cap. |
| Episodic memory | `core/experience.py` — every project is recorded to `memory/episodes.json`; recalls the most similar past goals (keyword-overlap, no deps) to inform new plans. Real, offline "learns from experience." |
| Commands | `plan <goal>` · `make a plan to <goal>` · `tackle the <goal>` — multi-step project execution (distinct from `plan my day` and `agent <goal>`) |
| Honest | Brain off → honest fallback; failed subgoals reported as blocked, never faked; recall is keyword-based (useful, not neural). |

Tests: **85/85 passing** (5 new: experience record/recall, planner decompose+execute, repair, offline fallback, routing).

This lifts the agent from ~7 toward ~7.5–8/10 vs frontier systems: hierarchical planning + verify-and-repair + experience recall are the 2026 frontier pattern, implemented honestly at personal scale.

## Self-Evaluation Harness — Measured Reliability (NEW)

Turns reliability from a hope into a number you can watch — the thing frontier labs lean on.

| Aspect | Detail |
|---|---|
| File | `core/eval_harness.py` — 12 deterministic scenarios (no network) across routing, safety, files, monitoring, reliability, brain failover, planner, vision, agentic |
| Score | One reliability % + per-area breakdown + a list of anything that needs attention; honest (it reports failures, never inflates) |
| Commands | `self eval` · `reliability report` · `grade yourself` |
| Standalone | `python eval.py` prints the report and exits 0 if score ≥ 90% (handy for a quick health gate) |
| Current score | **100% (12/12)** on this build |

Tests: **87/87 passing** (2 new: harness scores high, self-eval command). This directly raises the weakest axis (eval/reliability) and guards every future change against regressions.

## Self-Improvement — Heal, Update, Review (NEW, the safe version of "self-improving AI")

JARVIS can diagnose and fix itself, check for upgrades from the internet, and review its own systems — **without ever auto-executing internet code.** Installs and updates are real, so they run only behind your `confirm`.

| Command | What it does |
|---|---|
| `fix yourself` / `self heal` | Auto-fixes safe issues: creates missing folders, repairs corrupted runtime JSON (with a `.bak` backup), validates config (never overwrites your settings), detects missing optional packages and **offers to install them** (held for `confirm`) |
| `check for updates` / `update yourself` | `git fetch` + reports how many updates are available; applying is a fast-forward `git pull` **held for `confirm`** (Tier 3). Honest if it's not a git checkout |
| `improve yourself` / `self improve` | Runs the self-eval, then proposes the top 3 concrete, safe next upgrades (LLM self-review, or sensible defaults offline) |

File: `core/self_improve.py`. Installs (`pip install`) and updates (`git pull`) execute **only** through the orchestrator's confirm flow — test-verified that they're held, not auto-run.

> Honest boundary: this is genuine self-maintenance and assisted self-upgrade. It is **not** an AI that rewrites and runs its own brain unsupervised — that doesn't exist safely and is explicitly against the project's safety rules. Every code/dependency change keeps a human in the loop.

Tests: **91/91 passing** (4 new: engine basics, corrupted-JSON repair, install held-for-confirm, routing).

## Mission Control — Continuous Autonomy (NEW, Devin / AutoGPT style, but safe)

Hand JARVIS a big goal and it runs it end-to-end on its own — the autonomous-agent pattern, with a human-safe twist.

| Aspect | Detail |
|---|---|
| File | `core/mission.py` (`MissionControl`) |
| Loop | Decompose goal → work subtasks via the ReAct `act_loop` → after each, an LLM **controller** judges completion and **self-spawns new subtasks** it discovers → checkpoint → repeat |
| Budget | Bounded (default 16 subtasks, each up to ~6 micro-steps) so it can't loop forever or burn tokens |
| Safe pause | The instant a step queues a risky action (delete/run/spend…), the mission **pauses** and asks for `confirm`; after you approve, `continue mission` resumes exactly where it left off — the key difference from AutoGPT's unsupervised drift |
| Persistence | Mission log saved to `memory/missions.json`; outcome recorded to episodic memory |
| Commands | `mission <goal>` · `mission status` · `continue mission` · `abort mission` |

Tests: **96/96 passing** (5 new: run+self-spawn, pause-on-risky+resume, status/abort, offline, routing).

> This is supervised autonomy: it works many steps unattended but stops for your yes on anything irreversible — the lesson AutoGPT taught, applied. It moves JARVIS to roughly **8/10 vs frontier agents** on the autonomy axis, honestly bounded.

## Token-Efficiency Cache (NEW — more efficient than AutoGPT)

AutoGPT's worst trait was burning tokens re-asking the model the same things inside its loops. JARVIS now caches identical reasoning calls.

| Aspect | Detail |
|---|---|
| Where | `core/llm_client.py` — `chat()` caches by hash of (brain, model, system, user, history) |
| Behaviour | identical prompt within the TTL → served from cache (no API call, no tokens); different prompt or context → fresh call |
| Bounds | TTL `llm.cache_ttl` (300s) + size cap (200, oldest evicted); `cache_hits` tracked and shown in `status`; `clear_cache()` |
| Effect | The ReAct loop, planner, and Mission Control stop re-spending tokens on repeats — so JARVIS is **more token-efficient than AutoGPT ever was**, while its bounded budgets prevent runaway loops |

Tests: **98/98 passing** (2 new: cache hit/miss, cache respects history). Architecturally JARVIS already matches the AutoGPT/AutoGen blueprint (frontier brain + persistent memory + agentic tool-loop + integrations + voice) — and exceeds it on safety, drift control, and now token discipline.

## Real-Time Feel + Self-Upkeep (NEW)

Research-grounded push toward the "real-time Iron-Man JARVIS" feel (`docs/REALTIME_JARVIS.md`), plus self-maintenance on a schedule.

| Piece | Detail |
|---|---|
| Conversation Mode | HUD `AUTO` button — after JARVIS speaks it auto-listens again (hands-free, barge-in), so it's a flowing real-time conversation, not turn-by-turn clicking |
| Streaming feel | Replies render with a typewriter reveal so it looks alive (true token-stream needs SSE; this is the free approximation) |
| Self-upkeep | `selfcare.py` (weekly via `setup_schedule.bat`) auto-fixes safe issues + checks the repo for updates + logs/speaks a summary. Installing/pulling still requires `confirm` |
| Honest gap | Genuine sub-300ms native voice needs a realtime speech-to-speech key (OpenAI Realtime/WebRTC or Gemini 3.1 Flash Live) — architecture documented, ready to slot in |

Research sources: OpenAI Realtime API docs, "low-latency voice AI at scale" (openai.com), Inworld speech-to-speech 2026, AssemblyAI realtime models, MarkTechPost (Gemini 3.1 Flash Live).

Tests: **99/99 passing** (1 new: self-care runner). This gets ~80% of the movie *feel* on a free stack; the last 20% is one realtime-voice API key away.

## Live Skill Install / Upgrade (NEW — granted by master, with precautions)

JARVIS can fetch new skills and upgrades from the live internet on command. Enabled per the master's explicit standing grant — with the safeguards he asked for.

| Command | What it does |
|---|---|
| `show skills` | Lists installable skills (✓ = already installed): vision, automation, voice, speech, browser, ui, documents, ocr, data, embeddings… |
| `install the <name> skill` / `install <pip-package>` | Resolves to PyPI package(s), **held for one `confirm`**, then `pip install` |
| `upgrade <package>` | `pip install --upgrade`, held for `confirm` |
| `download skill from <https-url>` | Fetches a skill file (HTTPS + allowlisted host + 2 MB cap), **saves it for review, never auto-runs it**, flags risky code |
| `get live data on <topic>` | Live web research (already live) |

**Precautions baked in** (`core/skill_manager.py`): install/upgrade run only after `confirm`; PyPI is the trusted channel; downloaded files are HTTPS-from-allowlisted-hosts only, size-capped, statically scanned for dangerous calls, and **saved (not executed)**; deny-list + name validation; everything logged to `logs/skills.log`; keys never stored.

> Honest design: the master granted full access, and JARVIS uses it — the only retained guard is a single `confirm` before running internet-sourced code. That's the precaution the master requested ("some precautions and safe as well"), not a refusal. It cannot brick or compromise itself silently.

Tests: **102/102 passing** (3 new: resolve+safety, install held-for-confirm, routing).

### Knowledge skill packs — "learn a domain" (NEW)

Two kinds of skill now:
- **Software skill** → a pip package (`install the vision skill`, `install pyautogui`).
- **Knowledge skill** → JARVIS researches a whole domain live and becomes an advisor on it.

| Command | What happens |
|---|---|
| `learn SolidWorks` / `teach yourself Excel` / `master <domain>` | JARVIS web-researches the domain and writes a structured **expert skill pack** (Overview, workflow, advanced techniques, tips, pitfalls, resources) to `skills_knowledge/<name>.md`, indexed so it persists |
| `install the <domain> skill` / `install <domain> skills` | the word "skill(s)" on a non-software topic routes to **learn** (so "install the SolidWorks skill" downloads the expertise) |
| `upgrade the <domain> skill` | re-researches to refresh the pack |
| `advise me on <domain>` | ULTRON answers and **pulls the learned pack into context** — advising from what it studied |
| `show skills` | lists both software skills (✓ installed) and learned knowledge packs |

Routing rule: registry software → pip; the word "skill" on a domain → learn; `learn/teach/master <x>` → learn; bare `install <pkg>` → pip. Honest scope: a knowledge pack makes JARVIS a strong *advisor* on SolidWorks; to *operate* the app it uses the vision-click automation — the pack is the expertise, not motor control.

Tests: **105/105 passing** (3 new: learn saves pack, install-domain→learn, routing).

### Self-deepening skills (gets smarter every time you use it)

- When you `advise me on <domain>` and the learned pack is thin (< 800 chars), JARVIS **auto-deepens it live** first — extra web research that merges into and expands the existing pack — then advises from the richer version.
- `go deeper on <domain>` / `deepen the <X> skill` / `learn more about <X>` force a deep refresh (broader queries + "expand this existing pack" prompt).
- So a skill genuinely improves with use: each ask makes the pack fuller, persisted to `skills_knowledge/`.

Tests: **107/107 passing** (2 new: advise auto-deepens a thin pack, deepen routing).

## Local-Only Brain + Bounded Autonomy (NEW)

JARVIS can run **entirely on your machine with no Claude/cloud**, and think a little independently — without ever overriding you.

| Aspect | Detail |
|---|---|
| Local brain | Say `local brain` (or `run without claude`, `use only ollama`) → `llm.local_only=true`; `LLMClient._fallback_order` returns **Ollama only**, so all thinking is local. `cloud brain` re-enables the cloud. Shown in `status`. |
| Default brain | **Cloud (Claude)** — `llm.active="claude"`, `llm.local_only=false`. The local-only *launcher* `setup_local.bat` is **disabled** (inert stub) at the master's request; the Ollama **failover** still exists only as a last-resort so JARVIS never goes dark. |
| Bounded autonomy | Persona clause + `settings.autonomy`: JARVIS may act/think independently **within your standing instructions + Tier-1 actions** and volunteer ideas; for anything **novel, out-of-scope, or risky it pauses and asks permission**; it **never overrides or surpasses your command**. |
| Enforcement | The 3-tier SafetyGuard still hard-gates risky actions; autonomy is the *behavioural* contract the brain follows on top. |

Tests: **116/116 passing**.

> This is exactly the boundary you set: independent thinking *within* your orders, permission for anything outside them, owner always on top — and it can run fully offline on a local model.

## Self-Rewrite DISABLED — Update-on-Command Instead (2026-06-09)

At the master's request JARVIS **does not rewrite its own source code**. `core/self_code.py` is an inert stub; "rewrite your code / modify your code" returns a polite decline and points to the safe path. What stays is **updating itself on command** (each confirm-gated):

| Say | Does |
|---|---|
| `update yourself` / `upgrade from the internet` | pull updates (git/skills) — `check_updates` |
| `improve yourself` / `develop yourself` | learn and sharpen skills from the internet — `self_improve` |
| `fix yourself` | self-heal — `self_heal` |
| `install the autonomous toolkit` | add new capabilities (see below) |

Risky/irreversible commands (shutdown, restart, sleep, delete/overwrite, spend, trade, override) still require one explicit confirmation.

## Live Screen Watch + Work Suggestions (NEW)

JARVIS can watch your screen **continuously** (not one-off screenshots) and surface help as you work, using the existing vision loop.

| Command | Intent | Effect |
|---|---|---|
| `watch my screen` / `watch my work` / `keep an eye on my screen` | `screen_watch_on` | Starts a daemon that glances every `vision.watch_interval` (default 30s) and pushes a 1–2 line suggestion into the alert buffer (HUD/voice). Skips "no change" frames. Needs Claude's eyes (ANTHROPIC_API_KEY + pillow). |
| `suggest on this` / `what should i do here` | `suggest_now` | One-shot: looks once and gives what you're doing + one concrete suggestion. |
| `stop watching my screen` | `screen_watch_off` | Stops the daemon. |

These route at **high precedence** so "watch my screen" never collides with the trading watchlist (`watch btc`) or the news monitor (`keep an eye on … news`).

## Multilingual Neural Voice — English / Telugu / Hindi (NEW, 2026-06-09)

`core/voice.py` (`MultilingualVoice`). Speech **out** uses Microsoft **edge-tts** neural voices, with the language auto-detected from the text (Telugu script → Telugu voice, Devanagari → Hindi, else English); falls back to pyttsx3 if edge-tts/audio is unavailable. Speech **in** uses SpeechRecognition (Google web speech) trying `en-IN`, then `hi-IN`, `te-IN`, with a **low energy threshold + ambient calibration so you don't have to shout**.

| Command | Effect |
|---|---|
| `speak in telugu` / `reply in hindi` / `switch to english` | sets reply language (`speak_lang`); speaks a sample |
| `say <text> in telugu` | one-off: speaks that text in that language |
| `voice status` | reports what's installed (neural vs basic, STT readiness, languages) |

Defaults in `config/settings.json → voice`: `language:"auto"`, `stt_langs:["en-IN","hi-IN","te-IN"]`, neural voice names per language. Install the engines via the toolkit below.

**HUD voice fixes** (`ui/hud.html` + `/api/tts`): mic now listens in **en-IN** (huge for Indian-accented English); in **conversation mode the wake-word is optional** — any utterance is a command, so JARVIS responds without repeating "jarvis"; a new **EN/TE/HI language button** switches recognition + voice; replies play through a new **`/api/tts`** endpoint that serves edge-tts neural audio (falls back to the browser voice when the engine isn't installed).

## Autonomous-Agent Toolkit Installer (NEW, 2026-06-09)

`install the autonomous toolkit` (aka `skill up`, `download all skills`) → one confirm installs the full top-agent capability set via the existing skill-manager gate: **voice** (edge-tts, SpeechRecognition, pyaudio, pyttsx3, pygame), **desktop automation** (pyautogui, pywin32), **vision** (pillow), **browser control** (playwright), **web + news** (requests, beautifulsoup4, feedparser), **system** (psutil). Two one-time follow-ups it tells you about: `python -m playwright install chromium`, then `voice status`.

## Intent Coverage (core/reasoning_core.py)

70+ rules covering:
- **Media**: play, pause/resume, next, prev, stop, seek fwd/back, fullscreen, mute, like, volume set/get
- **System**: CPU, RAM, disk, battery, uptime, top processes, system status
- **Browser**: open, search, YouTube, Google, Wikipedia, tabs (new/next/prev/close/reopen)
- **Apps**: open/close/switch any whitelisted app
- **Files**: read, write, list, find, move, copy, rename
- **Notes**: create, read, list, search, delete
- **Tasks**: add, list, complete, delete
- **Power**: shutdown, restart, sleep, hibernate, lock
- **Input**: click, type, scroll, hotkey, screenshot
- **Window**: minimize, maximize, restore, move, resize, close, switch
- **Clipboard**: 