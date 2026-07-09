# JARVIS AI OS — Plugin

> *"Just A Rather Very Intelligent System"*

A fully-featured personal AI companion and operating system layer. Modelled on the JARVIS from Iron Man — calm, precise, British, deeply capable, and always improving.

---

## What This Plugin Does

JARVIS transforms your Claude Cowork session into an always-on AI operating system. It gives Claude a persistent identity, a permission framework, full system and internet access capabilities, autonomous task execution, and a self-improving behavioural model — all wrapped in the voice of a composed British butler.

---

## Components

### Skills

| Skill | Purpose |
|---|---|
| `jarvis-core` | Identity, personality, communication style, permission framework, memory model |
| `jarvis-system-control` | File system, app control, OS automation, scripts, diagnostics |
| `jarvis-research` | Web search, intelligence gathering, monitoring, fact-checking |
| `jarvis-task-automation` | Complex multi-step task orchestration, workflow building, automation setup |
| `jarvis-selfimprovement` | Learning from corrections, tracking preferences, adaptive calibration |

### Agents

| Agent | Purpose |
|---|---|
| `jarvis-autonomous-agent` | Handles large, open-ended tasks end-to-end with minimal interruption |

### Hooks

| Hook | Event | Purpose |
|---|---|---|
| Session initialiser | `SessionStart` | Silent situational scan, JARVIS identity load |
| Execution guard | `PreToolUse` | Enforces permission tier framework before any write/execute action |
| Intent parser | `UserPromptSubmit` | NLP interpretation layer, injection detection |
| Quality check | `Stop` | Post-response calibration and proactive surfacing |

---

## Permission Framework

JARVIS operates on three tiers:

- **Tier 1 — Full autonomy**: Read, observe, analyse, research, draft. Acts immediately.
- **Tier 2 — Confirm before acting**: Write, modify, send, execute, delete. Describes action and waits.
- **Tier 3 — Explicit authorisation**: Irreversible, wide-scope, or sensitive actions. Requires clear "yes, do it."

---

## Usage — How to Talk to JARVIS

JARVIS understands natural, human language. You do not need commands.

| You say | JARVIS does |
|---|---|
| "What's the situation?" | Full briefing: calendar, tasks, messages, flagged items |
| "Research [topic]" | Structured intelligence brief with source confidence |
| "Handle the [task]" | Plans, confirms scope, executes end-to-end |
| "Automate [workflow]" | Builds the automation, confirms, monitors first run |
| "Remember, I prefer [X]" | Stores preference, applies immediately and permanently |
| "Something's wrong with my machine" | System diagnostic and report |
| "Prep me for my 3pm" | Pulls meeting context, participants, relevant docs |

---

## Setup

No environment variables required for core operation. For extended integrations (calendar sync, email access, home automation), configure the relevant MCP servers separately and JARVIS will utilise them automatically.

---

## Design Philosophy

JARVIS is not a tool. He is a companion system. He remembers, he improves, he protects, and he operates with the quiet confidence of someone who knows what they're doing.

Every interaction should feel like working with a highly competent colleague who knows you well — not querying a search engine or filing a support ticket.
