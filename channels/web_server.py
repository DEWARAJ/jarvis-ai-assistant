"""Local web server bridge for the JARVIS dashboard.

Pure standard library (http.server) — no Flask, no pip installs. Serves the
Iron-Man-style dashboard and exposes a tiny JSON API that drives the same
Orchestrator used by terminal mode. Voice runs in the browser (Web Speech API),
so there's nothing to install for speech.

Endpoints:
  GET  /                -> dashboard.html
  GET  /api/bootstrap   -> banner, agents, tools, status, llm status
  POST /api/command     -> {"text": "..."} -> {"reply": "...", "status": {...}}
"""
from __future__ import annotations
import json, os, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core.orchestrator import Orchestrator

UI_PATH = os.path.join("ui", "hud.html")          # movie-grade JARVIS HUD (default)
CLASSIC_PATH = os.path.join("ui", "dashboard.html")  # classic dashboard at /classic
_LOCK = threading.Lock()


class _Handler(BaseHTTPRequestHandler):
    orch: Orchestrator = None  # set by serve()

    # quieter logging
    def log_message(self, fmt, *args):
        try:
            self.orch.logger.info("web " + (fmt % args))
        except Exception:
            pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            # Client closed the connection before we finished (e.g. superseded
            # request, page refresh). Nothing to send — ignore quietly.
            pass

    def _status_dict(self):
        o = self.orch
        return {
            "version": o.settings.get("version", "?"),
            "agents": len(o.agents.names()),
            "tools": len(o.tools.names()),
            "open_tasks": o.tasks.open_count(),
            "voice_on": o.voice_on,
            "llm": o.llm.status(),
            "llm_enabled": o.llm.enabled,
            "brain": o.llm.active,
            "mode": getattr(o, "mode", "balanced"),
            "live": o.live.snapshot() if hasattr(o, "live") else {},
        }

    def do_GET(self):
        if self.path in ("/", "/index.html", "/dashboard"):
            try:
                with open(UI_PATH, encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(500, "<h1>dashboard.html not found</h1>", "text/html")
            return
        if self.path == "/classic":
            try:
                with open(CLASSIC_PATH, encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(500, "<h1>dashboard.html not found</h1>", "text/html")
            return
        if self.path == "/api/greeting":
            o = self.orch
            try:
                greet = o._time_greeting()
                recap = ""
                try:
                    eps = o.jmem.recent_episodes(n=1)   # v3: situational recall on boot
                    if eps:
                        recap = " Last session: " + (eps[-1].get("summary", "")[:120])
                except Exception:
                    pass
                briefing = ""
                try:
                    briefing = o.startup_greeting()
                except Exception:
                    pass
                payload = {"greeting": greet + recap, "slot": o._greeting_slot(), "briefing": briefing}
            except Exception:
                payload = {"greeting": "", "slot": "", "briefing": ""}
            self._send(200, json.dumps(payload)); return
        if self.path == "/api/status":
            self._send(200, json.dumps(self._status_dict()))
            return
        if self.path == "/api/alerts":
            try:
                alerts = self.orch.drain_alerts()
            except Exception:
                alerts = []
            self._send(200, json.dumps({"alerts": alerts}))
            return
        if self.path == "/api/bootstrap":
            o = self.orch
            payload = {
                "banner": o.settings.get("boot_banner", "JARVIS OS ONLINE"),
                "agents": o.agents.describe(),
                "tools": o.tools.names(),
                "status": self._status_dict(),
            }
            self._send(200, json.dumps(payload))
            return
        if self.path.startswith("/api/tts"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            text = (q.get("text", [""])[0]).strip()
            lang = (q.get("lang", [""])[0]).strip() or None
            eng = getattr(self.orch, "voice_engine", None)
            if eng and text:
                try:
                    fp = eng.synth_to_file(text, lang=lang)
                    if fp:
                        with open(fp, "rb") as f:
                            self._send(200, f.read(), "audio/mpeg")
                        return
                except Exception:
                    pass
            self._send(204, b"", "audio/mpeg")   # no neural audio -> HUD uses browser voice
            return
        self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/api/command":
            self._send(404, json.dumps({"error": "not found"}))
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            text = (json.loads(raw).get("text") or "").strip()
        except (ValueError, json.JSONDecodeError):
            self._send(400, json.dumps({"error": "bad request"}))
            return
        if not text:
            self._send(200, json.dumps({"reply": "Say something, Master.", "status": self._status_dict()}))
            return
        # No module lock here: orch.handle() is now single-flight internally (it claims a
        # turn epoch, serializes on its own lock, and DROPS a turn that a newer command
        # supersedes). Wrapping it in _LOCK would block a newer command from claiming its
        # epoch until the old one finished — defeating supersede. So call it directly.
        try:
            reply = self.orch.handle(text)
        except Exception as e:
            reply = f"[!] Error (logged): {e}"
        if not reply:
            # Superseded by a newer command (or empty) — tell the client to ignore this
            # stale turn so it never renders or speaks a previous answer.
            self._send(200, json.dumps({"superseded": True, "reply": "",
                                        "status": self._status_dict()}))
            return
        payload = {"reply": reply, "status": self._status_dict(),
                   "running": self.orch.running}
        self._send(200, json.dumps(payload))


def serve(host="127.0.0.1", port=8765, open_browser=True):
    orch = Orchestrator()
    _Handler.orch = orch
    try:
        orch.start_monitor()
    except Exception:
        pass
    try:
        orch.start_autonomy_if_enabled()
    except Exception:
        pass
    httpd = ThreadingHTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}/"
    print("=" * 56)
    print(f"   {orch.settings.get('boot_banner', 'JARVIS OS ONLINE')}")
    print(f"   Dashboard live at:  {url}")
    print("   Voice runs in your browser (use Chrome or Edge).")
    print("   Press Ctrl+C here to stop the server.")
    print("=" * 56)
    if open_browser:
        try:
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nJARVIS dashboard stopped. Goodbye, Master.")
    finally:
        httpd.server_close()
