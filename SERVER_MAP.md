# JARVIS Server Map

## channels/web_server.py — port 8765 — WEB DASHBOARD / HUD
Purpose: serves the Iron-Man HUD (ui/hud.html) and the JSON API that drives the
orchestrator. Voice runs in the browser (Web Speech API).
Endpoints:
  GET  /                -> ui/hud.html  (HUD; /classic -> ui/dashboard.html)
  GET  /api/bootstrap   -> banner, agents, tools, status
  GET  /api/status      -> live status snapshot (LiveStatus.snapshot) + system stats
  GET  /api/greeting    -> time-based greeting + boot briefing
  GET  /api/alerts      -> drained alerts
  GET  /api/tts         -> neural TTS audio (optional)
  POST /api/command     -> {"text": "..."} -> {"reply", "status", "running"}
Start: main.py -> channels.web_server.serve()  (default mode)

## channels/remote_server.py — port 8765 (LAN bind) — REMOTE CONTROL
Purpose: authenticated LAN-only command channel (e.g. the master's phone).
Refuses to start without JARVIS_REMOTE_TOKEN. Token-gated, rate-limited, audited.
Class B actions stay confirm-gated (runs through orchestrator.handle()).
Endpoints:
  GET  /health   -> {"ok": true}  (no auth)
  POST /command  -> bearer-token required -> {"reply"}
Start: orchestrator.start_remote_if_enabled() when config remote.enabled = true.
Note: same default port as the dashboard — only one of the two runs at a time
(dashboard for local use; remote for phone/LAN). Set a distinct port if running both.

## local_api.py — port 7799 — COMMAND API  (DEPRECATED)
Purpose: HTTP REST API built for the deprecated jarvis_main.py system.
Status: NOT started by main.py / orchestrator. Superseded by web_server.py /api/command.
Decision: kept for reference; do not wire into the orchestrator. Remove once confirmed
no external client depends on port 7799.
