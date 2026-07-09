# JARVIS Cognition — v2.0 + v3.0 Architecture

Persistent memory · OODA · self-adaptation · independent thinking · military-grade security.
All of this is integrated into the **existing** JARVIS (no separate runtime). Built on the
working orchestrator, tools, and `llm_client` — not a rewrite.

---

## New modules (core/)

| Module | Purpose |
|---|---|
| `jarvis_memory.py` | 4-tier persistent memory (episodic / semantic / code-changelog) + boot briefing. Secrets redacted on write; JSONL append-only; atomic `semantic.json`. |
| `ooda_loop.py` | Observe → Orient → Decide → Act engine. Memory recall, approach generation (LLM-assisted), Class-B/code-mod/web flags, `[OBS]/[ORI]/[DEC]/[ACT]` narration. |
| `adapt_engine.py` | Self-modification: `propose()` → approve → `apply()`. Backup + `py_compile` + smoke test + **auto-rollback**. Path-locked to project root. Uses `llm_client` (no hardcoded key). |
| `independent_thinking.py` | 5-point review (challenge/feasibility/better-path/risk/memory), `[JARVIS DISAGREES]` format, `/think` reasoning-only mode. |
| `security_audit.py` | `SecurityClassifier` (A/B/C/X) + `AuditLog` (SHA256-chained, tamper-evident `security/audit_log.jsonl`). |
| `mission_engine.py` | Goal → ≤7 phases with assigned LLM, decision gates, abort triggers, rollback. Plan-only (no execution). |

`tests/smoke_tests.py` — post-mutation validator the adapt engine runs (8 checks). Run manually:
`.venv\Scripts\python.exe tests\smoke_tests.py`

---

## Memory tiers (memory/)

| Tier | File | Holds |
|---|---|---|
| 1 Session | RAM (orchestrator `history`) | active conversation |
| 2 Episodic | `episodic.jsonl` | session summaries: ts, session_id, summary, decisions, tasks_completed, errors, mood |
| 3 Semantic | `semantic.json` | user_profile {name, goals, preferences, projects}, learned_patterns, world_model |
| 4 Code | `code_changelog.jsonl` | every self-mutation: ts, trigger, files_modified, diff_summary, test_result, rolled_back |

- **Boot:** orchestrator builds `self.memory_briefing`; `startup_greeting()` is shown on terminal start and rides the `/api/greeting` payload (recap + `briefing`) in the GUI/HUD.
- **Auto-save:** an episodic summary is written every 10 exchanges, on `/save`, and on `/exit`.
- **Dew profile** is seeded into semantic memory once (`_seed_dew_profile`, idempotent).

---

## Security model

| Class | Meaning | Enforcement |
|---|---|---|
| A | Autonomous (read/search/analyse/code-gen) | runs, no ask |
| B | One confirmation | existing SafetyGuard/permission + logged via `_run_pending` |
| C | Double confirmation (`<action> confirm`) | HIGH-risk core-file self-adapts require `approve adapt confirm` |
| X | Hard block (never executes) | blocked at the command interceptor + logged to audit chain |

Audit log is append-only with a SHA256 hash chain — any edit/deletion of a past entry breaks
verification (`/security` reports chain health). Class B/C actions through the confirm
chokepoint and all self-adapts are recorded; pure Class-A calls are not (by design).

---

## Commands

```
/memory      full memory briefing            /OODA <task>   run a task through OODA
/save        force episodic save             /think <q>     reasoning only, no action
/history [n] recent episodes                 /adapt <file> <task>  self-modify (gated)
/status      active projects                 /rollback <file>      restore last backup
/changelog   code mutation history           /mission <goal>       7-phase plan
/forget <k>  remove a semantic key           /plan <goal>          mission plan (preview)
/security    audit chain + recent actions    /research <topic>     LLM research
/model <task> show routed brain              /build <spec>         build mission plan
/trade status|activate|halt  (no live orders — activation is gated)
/exit        clean shutdown + memory save
"full power" -> Iron Man protocol (proactive mode + briefing)
```

---

## Enabling the LLM-dependent features

OODA orient, `/research`, `/think`, mission decomposition, and the **self-adapt code
generator** call the brain via `llm_client`. They degrade gracefully when offline, but for
full power set a provider key in the env named by the active profile in
`config/settings.json` (e.g. `ANTHROPIC_API_KEY`). Self-adaptation cannot generate code
without it.

`/model <task>` shows which brain would be routed (Claude reasoning, Perplexity live web,
Haiku ops, Ollama local fallback).

---

## Hard constraints (in the persona, cannot be overridden)

Loyalty to Dew · honesty over comfort · OODA before acting · security-first gating ·
never fake capability · memory is sacred. Trading: <=2% risk/trade, auto-halt at 5% daily
loss, no overnight leverage without instruction, never report paper as real, P&L never hidden.
Self-modification of the identity laws or security gates = Class X (blocked).
