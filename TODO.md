# JARVIS OS — TODO
_Last updated: 2026-06-09_

## Phase 1 ✅ COMPLETE

- [x] `main.py` — JARVIS OS ONLINE banner + basic command loop
- [x] Orchestrator — OODA dispatch, tool registry wiring
- [x] ReasoningCore — 70+ intent rules across all domains
- [x] SafetyGuard — 3-tier model + injection detection + audit log
- [x] YoutubeTool — next/prev/stop/seek/fullscreen (3-layer fallback)
- [x] VolumeControlTool — exact % via pycaw, VK coarse fallback
- [x] SystemInfoTool — CPU/RAM/disk/battery/network diagnostics
- [x] config/tools.json — all tools registered
- [x] Orchestrator dispatch — all media/system/volume intents wired

---

## Companion Layer ✅ COMPLETE

- [x] Time-aware greetings (morning/afternoon/evening/night) — in-app
- [x] Auto-greeting on dashboard, once per slot (localStorage guard)
- [x] Clap-to-wake (Web Audio peak detection)
- [x] Weather on demand (`weather`, `weather in <city>` — wttr.in, no key)
- [x] Traffic on demand (`traffic to <place>` — live Google Maps)
- [x] **Scheduled greetings when app is closed** — `daily_greeting.py` + `setup_schedule.bat` (Windows Task Scheduler, 08:00 / 13:00 / 18:00 / 22:00, speaks via SAPI)
- [x] **Midday weather + traffic check (1 PM)** — speaks live weather; opens live Google Maps traffic for your commute when `companion.commute_to` is set in settings.json

> Setup: double-click `setup_schedule.bat` once. Remove with `remove_schedule.bat`.
> Commute traffic: set `companion.commute_to` in `config/settings.json`.

---

## ULTRON Advisor ✅ COMPLETE

- [x] `agents/ultron_agent.py` — advanced research/strategy/advice sub-agent (advises only, never executes; loyal, safety-bound)
- [x] Pulls **live web references** (search + fetch) and synthesizes with citation
- [x] Actions: research, advise, improve, deep_think, check_in
- [x] Registered in `config/agents.json`; intents in `reasoning_core.py`; handlers in `orchestrator.py`
- [x] `research` now delegates to ULTRON; daily briefing offers ULTRON
- [x] Proactive butler: `what should I do next` advises **and asks** a focusing question
- [x] 3 new tests (registration, intent routing, graceful-offline) — 35/35 passing

> Try: `advise me on <task>` · `how do I improve <X>` · `what should I do next` · `ultron research <topic>`

---

## Built to `jarvis-ai-os` Plugin ✅ COMPLETE

- [x] Plugin bundled at `plugin/jarvis-ai-os/`; mapping in `docs/PLUGIN_ALIGNMENT.md`
- [x] Persona rewritten to `jarvis-core` (identity, British voice, forbidden/signature phrases, advice, proactivity, security)
- [x] Explicit 3-tier permission framework (Tier 1 autonomy / Tier 2 confirm / Tier 3 explicit) + `tier3_explicit` set
- [x] ULTRON upgraded with `jarvis-research` methodology (triangulation, A/B/C confidence)
- [x] Autonomous execution mode (`jarvis-autonomous-agent`): `handle <task> end to end`, `just get it done`, `take care of it`
- [x] `what's the situation` / `sitrep` situational briefing
- [x] 4 new tests — 39/39 passing

> Optional next: install the plugin Claude-side (Settings → Capabilities) for the same identity in chat.

---

## Road to 9/10 — Upgrade 1 of 6 ✅ COMPLETE: LLM Tool-Calling Brain

- [x] `core/agentic_core.py` — LLM understands intent, returns JSON plan, orchestrator runs the steps
- [x] ~38-action catalog mapped to real intents; multi-step chaining (≤4 steps)
- [x] Routed through `_freeform`; rule-based fast-path kept for instant commands
- [x] Safety preserved — brain-planned risky actions held for confirmation (test-verified)
- [x] Graceful: invalid JSON → spoken answer; offline → fallback; `llm.agentic` toggle
- [x] 5 new tests — 44/44 passing

## Road to 9/10 — Upgrade 2 of 6 ✅ COMPLETE: Reliability

- [x] `core/reliability.py` — verify results, honest retry, action logging
- [x] `_run_action` self-verifies; read-only actions retry once; side effects never blind-retried
- [x] Failures reported honestly (never faked); outcomes logged to `logs/actions.log`
- [x] `doctor` — full live self-diagnostic (deps, keys, network, brain, tools/agents)
- [x] 4 new tests — 48/48 passing

## Road to 9/10 — Upgrade 3 of 6 ✅ COMPLETE: Never Go Dumb (multi-brain failover)

- [x] `LLMClient.chat()` resilient — active brain → auto-failover → local Ollama floor
- [x] Health cache w/ cooldown (skip known-down brains); key-aware (skip brains without keys)
- [x] `last_brain` / `last_failover` surfaced in `status` + `doctor`; `llm.fallback` config
- [x] Every caller (orchestrator, ULTRON, agentic, research) benefits automatically
- [x] 4 new tests — 52/52 passing

## Road to 9/10 — Upgrade 4 of 6 ✅ COMPLETE: Real Senses

- [x] `core/vision_core.py` — capture → look → verify loop
- [x] `see my screen` / `verify <X>` commands; honest YES/NO/unclear verdicts
- [x] `see_screen` + `verify_screen` in the agentic catalog — brain can act→look→verify
- [x] Dashboard wake-word gating (say "Jarvis …") + calmer butler voice
- [x] `voice.wake_word` + `vision` config; graceful without pillow / vision key
- [x] 4 new tests — 56/56 passing

## Road to 9/10 — Upgrade 5 of 6 ✅ COMPLETE: Proactive Autonomy

- [x] `core/watch_manager.py` — price/system/news/url watchers, thresholds, change detection, cooldown, persistence
- [x] Background monitor thread (`start_monitor`, opt-in) → alerts buffer → `/api/alerts` → dashboard surfaces + speaks
- [x] Commands: `monitor … below/above N`, `monitor disk/battery/cpu`, `watch news about …`, `watch the page <url>`, `show monitors`, `stop monitoring <id>`, `anything new`
- [x] Read-only/Tier 1; bare `watch`/`watchlist` still = trading watchlist
- [x] 7 new tests — 63/63 passing

## Road to 9/10 — Upgrade 6 of 6 ✅ COMPLETE: Depth over Breadth

- [x] `core/workflows.py` — robust multi-step engine (live status, retry, honest partial delivery)
- [x] `start my day`, `wind down`, `focus on <task>`, `research brief on <topic>` (saves a .md file)
- [x] `wf_start_day` + `wf_research_brief` brain-callable; high-precedence intents
- [x] 5 new tests — 68/68 passing

## 🎯 Road to 9/10 — ALL 6 UPGRADES COMPLETE

1. ✅ LLM tool-calling brain
2. ✅ Reliability (self-verify + doctor)
3. ✅ Never go dumb (multi-brain failover)
4. ✅ Real senses (vision look→verify, wake word, voice)
5. ✅ Proactive autonomy (background monitoring)
6. ✅ Depth over breadth (daily workflows)

> 68/68 tests passing. Honest cap: a flawless sci-fi JARVIS isn't achievable; this is the strong real-world ~9/10 — and it degrades honestly instead of faking success.

## Toward Frontier Agents ✅ (ReAct loop + vision control)

- [x] `agentic_core.act_loop` — true observe→think→act→observe loop with self-correction (≤6 steps, summary + transcript)
- [x] `handle this end to end` / `agent <goal>` now run the loop
- [x] `vision_core.locate` + `click the <X>` / `click_vision` — sees a target and clicks it
- [x] Safety preserved every step; honest when it can't see/click; 8 new tests — 76/76 passing
- [x] **Masterpiece grounding** — UIA accessibility-tree (exact) → two-pass "zoom and confirm" vision → single-pass fallback; method reported; `vision.two_pass` config; 80/80 tests
- [x] **Long-horizon planner** — `core/planner.py`: subgoal decomposition + verify-and-repair, beyond the 6-step cap (`plan <goal>` / `tackle <goal>`)
- [x] **Episodic memory** — `core/experience.py`: records every project, recalls similar past goals to inform new plans (learns with use)
- [x] 5 new tests — 85/85 passing
- [x] **Self-eval harness** — `core/eval_harness.py` + `python eval.py`: 12 scenarios scored as a reliability % (currently 100%); `self eval` command
- [x] **Self-improvement** — `core/self_improve.py`: `fix yourself` (heal + repair + detect deps), `check for updates` (git, confirm-gated), `improve yourself` (self-review). Installs/updates always behind `confirm`. 91/91 tests.
- [ ] Future: real-time speech-to-speech voice; neural vector memory; smart-home bridge (see docs/BLUEPRINT.md)

> Note: true unsupervised self-rewriting AI is intentionally NOT built — unsafe and against the project rules. JARVIS self-maintains and self-upgrades with the master in the loop.

## Mission Control ✅ (continuous autonomy, Devin/AutoGPT style)

- [x] `core/mission.py` — decompose → run subtasks via ReAct → controller self-spawns subtasks → bounded budget
- [x] Safe pause on risky steps → `confirm` → `continue mission` resumes; mission log persisted; episode recorded
- [x] Commands: `mission <goal>` / `mission status` / `continue mission` / `abort mission`
- [x] 5 new tests — 96/96 passing

## Token-efficiency cache ✅ (more efficient than AutoGPT)

- [x] `core/llm_client.py` response cache — identical reasoning calls served free (TTL + size cap), `cache_hits` in `status`, `clear_cache()`
- [x] 2 new tests — 98/98 passing
- [x] Architecture confirmed to match the AutoGPT/AutoGen blueprint (brain + memory + agentic loop + integrations + voice), exceeding it on safety + drift + token discipline

## Real-time feel + self-upkeep ✅

- [x] `docs/REALTIME_JARVIS.md` — research-backed: what makes it real-time + the achievable vs key-needed path
- [x] HUD Conversation Mode (`AUTO`) — hands-free continuous voice loop with barge-in
- [x] Typewriter streaming feel for replies
- [x] `selfcare.py` + weekly schedule — auto-heal + update check (applies stay confirm-gated)
- [x] 99/99 tests passing
- [ ] Future (true sub-300ms voice): wire OpenAI Realtime (WebRTC) or Gemini Live with an API key

## Live skill install / upgrade ✅ (granted, with precautions)

- [x] `core/skill_manager.py` — `show skills`, `install the <skill> skill` / `install <pkg>`, `upgrade <pkg>`, `download skill from <https-url>`
- [x] Installs/upgrades from PyPI, held for one `confirm`; downloads HTTPS+allowlisted+scanned+saved (never auto-run); deny-list; logged to `logs/skills.log`
- [x] `get live data on <topic>` live research alias; Gemini added as a switchable brain
- [x] 3 new tests — 102/102 passing

## Knowledge skill packs ✅ (learn a domain like SolidWorks)

- [x] `SkillManager.learn(topic)` — live research → expert pack saved to `skills_knowledge/` + index + recall
- [x] `learn/teach yourself/master <domain>` and `install the <domain> skill` route to learning; `upgrade the <domain> skill` refreshes
- [x] `advise me on <domain>` pulls the learned pack into ULTRON's context
- [x] `show skills` lists software + learned knowledge skills
- [x] 3 new tests — 105/105 passing

## Self-deepening skills ✅ (smarter with use)

- [x] `advise me on <domain>` auto-deepens a thin pack live (merges new research into the existing pack)
- [x] `go deeper on <X>` / `deepen the <X> skill` / `learn more about <X>` force a deep refresh
- [x] 2 new tests — 107/107 passing

## Local-only brain + bounded autonomy ✅

- [x] `local brain` / `run without claude` → Ollama-only thinking (`llm.local_only`); `cloud brain` reverts; `setup_local.bat`
- [x] Autonomy clause: independent within standing instructions + Tier-1; asks permission for out-of-scope/novel/risky; never overrides owner
- [x] 4 new tests — 111/111 passing
- [ ] Optional: a small local embedding model so the local brain has neural memory too

## Multilingual voice + toolkit + self-rewrite off ✅ (2026-06-09)

- [x] Self-rewrite disabled (`core/self_code.py` inert); "rewrite your code" politely declines and points to updates
- [x] `update yourself` / `improve yourself` / `fix yourself` keep working (confirm-gated); risky cmds still gated
- [x] `core/voice.py` — neural multilingual voice: edge-tts (English/Telugu/Hindi) with auto language detection + pyttsx3 fallback
- [x] Speech input via SpeechRecognition (en-IN→hi-IN→te-IN), low energy threshold + ambient calibration (no shouting)
- [x] Commands: `speak in telugu/hindi/english`, `say <x> in <lang>`, `voice status`
- [x] HUD: mic now en-IN, wake-word optional in conversation mode, EN/TE/HI language button, `/api/tts` neural audio
- [x] `install the autonomous toolkit` — one-confirm install of the full top-agent package set
- [x] Fixed `_extract_args` (missing break), restored `_help` + 3-tier status line after edit-tool truncations
- [x] 5 new/updated tests — 116/116 passing
- [ ] Optional: bundle a one-click `setup_voice.bat` (pip the toolkit + `playwright install chromium`)

## Self-code + live screen watch ✅ (2026-06-09)

- [x] ~~`core/self_code.py` self-rewrite~~ — **REMOVED 2026-06-09** at master's request (inert stub); kept update-on-command instead
- [x] Intents `self_code` / `screen_watch_on` / `screen_watch_off` / `suggest_now`, wired in orchestrator + `_run_pending`
- [x] `watch my screen` continuous daemon (every ~30s) → suggestions into the alert buffer; `suggest on this` one-shot
- [x] High-precedence routing so it never collides with `watch btc` / news monitors
- [x] Cloud is the default brain again (`active="claude"`, `local_only=false`); `setup_local.bat` disabled to an inert stub per master
- [x] 4 new tests — 115/115 passing
- [ ] Optional: let self-code edit + auto-run the test suite before offering `confirm`
- [ ] Optional: a "revert last self-code change" command that restores the newest `.bak`

---

## Phase 2 — Voice & GUI

- [ ] Wake-word listener (offline, e.g. Porcupine or Whisper tiny)
- [ ] Real-time TTS with voice selection
- [ ] Floating HUD (system tray or overlay window)
- [ ] Streaming LLM responses displayed in GUI

## Phase 3 — Advanced Intelligence

- [ ] Long-term episodic memory (vector store, e.g. ChromaDB)
- [ ] Proactive alerts (battery low, meeting in 5 min, news brief on schedule)
- [ ] Multi-step plan executor with rollback
- [ ] LLM fallback for unrecognized intents (not just "unknown")
- [ ] Pluggable specialist agents (trading, research, coding, e-commerce)

## Phase 4 — Integrations

- [ ] Gmail / Outlook read + compose (with confirmation gate)
- [ ] Google Calendar read + event creation
- [ ] Notion / Obsidian notes sync
- [ ] Spotify / system media player native SDK
- [ ] Home automation (smart lights, thermostat via local API)

## Phase 5 — Self-Improvement

- [ ] Intent miss logging → fine-tune ReasoningCore rules
- [ ] Automate