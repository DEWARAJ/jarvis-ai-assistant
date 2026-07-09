"""
local_api.py  —  JARVIS v7.0
Local HTTP API on port 7799.

Any client (terminal, web UI, phone, Hermes) can send commands
to JARVIS and receive responses via HTTP.

Endpoints:
  POST /command   {"command": "..."}  -> {"status": "queued"}
  GET  /status    -> CPU/RAM snapshot
  GET  /memory    -> last 20 episodic entries
  POST /hermes    {"content": "..."}  -> Hermes pushes task to JARVIS
  GET  /alerts    -> pending alerts
  GET  /health    -> {"status": "online"}
"""
from __future__ import annotations
import json, queue, threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

_command_queue: queue.Queue | None = None
_alert_store:   list = []


def _set_command_queue(q: queue.Queue) -> None:
    global _command_queue
    _command_queue = q


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default access log

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self._ok({"status": "online",
                       "timestamp": datetime.now().isoformat()})

        elif path == "/status":
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=0.3)
                ram = psutil.virtual_memory()
                self._ok({"cpu_pct": cpu, "ram_pct": ram.percent,
                           "timestamp": datetime.now().isoformat()})
            except Exception as e:
                self._ok({"error": str(e)})

        elif path == "/memory":
            from pathlib import Path
            ep      = Path("memory/episodic.jsonl")
            entries = []
            if ep.exists():
                try:
                    with ep.open(encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    entries.append(json.loads(line))
                                except Exception:
                                    pass
                    entries = entries[-20:]
                except OSError:
                    pass
            self._ok({"entries": entries})

        elif path == "/alerts":
            self._ok({"alerts": _alert_store[-10:]})

        else:
            self._err(404, "Not found")

    def do_POST(self):
        path   = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length).decode("utf-8") if length else ""
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._err(400, "Invalid JSON"); return

        if path == "/command":
            cmd = data.get("command", "").strip()
            if not cmd:
                self._err(400, "No command provided"); return
            if _command_queue is not None:
                _command_queue.put(("api", cmd))
            self._ok({"status": "queued", "command": cmd})

        elif path == "/hermes":
            task = data.get("content", data.get("task", "")).strip()
            if not task:
                self._err(400, "No content provided"); return
            if _command_queue is not None:
                _command_queue.put(("hermes", f"[FROM HERMES] {task}"))
            self._ok({"status": "received"})

        else:
            self._err(404, "Not found")

    def _ok(self, data: dict, code: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _err(self, code: int, msg: str) -> None:
        self._ok({"error": msg}, code)


def start_api_server(
    command_queue: queue.Queue, port: int = 7799
) -> threading.Thread:
    """Start local API in daemon thread. Call at jarvis_main.run() boot."""
    _set_command_queue(command_queue)
    server = HTTPServer(("127.0.0.1", port), _Handler)

    def _run():
        print(f"[API] JARVIS local API → http://127.0.0.1:{port}")
        server.serve_forever()

    t = threading.Thread(target=_run, daemon=True, name="JARVIS-LocalAPI")
    t.start()
    return t
