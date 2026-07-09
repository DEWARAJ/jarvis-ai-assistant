"""Phase 4 — authenticated LAN-only remote control (e.g. the master's phone).

Hard rules (from the hardening prompt):
  - ONLY the verified master may issue commands. Every request must carry the correct
    bearer token (JARVIS_REMOTE_TOKEN, read from the environment, never stored in config).
  - NEVER an unauthenticated inbound path. No token in the environment => the server
    REFUSES to start. A wrong/missing token => 401, command never reaches the brain.
  - LAN-only. Bind on the local network; keep it behind your router (no port-forwarding).
    There is no internet relay here by design.
  - Class B stays Class B remotely. Commands run through orch.handle(), so the normal
    permission gate + self.pending confirm flow applies — a remote 'delete'/'shutdown'
    is HELD and only runs after a separate remote 'confirm'. Phrasing/urgency over the
    wire does not change an action's class.

Pure standard library (http.server) — no new dependencies. Token comparison is
constant-time. Every request is audited.
"""
from __future__ import annotations
import os, json, time, hmac, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class RemoteControl:
    def __init__(self, orch, token: str | None = None, host: str = "0.0.0.0",
                 port: int = 8765, rate_limit: int = 30):
        self.orch = orch
        self.token = token if token is not None else os.environ.get("JARVIS_REMOTE_TOKEN", "")
        self.host = host
        self.port = int(port)
        self.rate_limit = int(rate_limit)        # max requests / minute / client IP
        self._hits: dict[str, list] = {}
        self._httpd = None
        self._thread = None

    # ---- auth ----
    def authorize(self, header_value: str | None) -> bool:
        """Constant-time bearer-token check. No token configured => always deny."""
        if not self.token:
            return False
        provided = (header_value or "")
        if provided.lower().startswith("bearer "):
            provided = provided[7:]
        provided = provided.strip()
        if not provided:
            return False
        return hmac.compare_digest(provided, self.token)

    def _rate_ok(self, ip: str) -> bool:
        now = time.time()
        window = [t for t in self._hits.get(ip, []) if now - t < 60]
        window.append(now)
        self._hits[ip] = window
        return len(window) <= self.rate_limit

    # ---- core request handling (transport-agnostic so it's unit-testable) ----
    def handle_request(self, token_header: str | None, text: str, client_ip: str = "test") -> dict:
        """Return {status, reply}. The HTTP layer is a thin wrapper over this."""
        if not self._rate_ok(client_ip):
            self._audit(client_ip, "RATE_LIMITED", text)
            return {"status": 429, "reply": "Too many requests."}
        if not self.authorize(token_header):
            self._audit(client_ip, "UNAUTHORIZED", text)
            return {"status": 401, "reply": "Unauthorized."}
        text = (text or "").strip()
        if not text:
            return {"status": 400, "reply": "Empty command."}
        self._audit(client_ip, "ACCEPTED", text)
        try:
            reply = self.orch.handle(text)          # full gate + pending/confirm flow applies
        except Exception as e:
            return {"status": 500, "reply": f"Error handling command: {e}"}
        return {"status": 200, "reply": reply}

    def _audit(self, ip: str, verdict: str, text: str) -> None:
        lg = getattr(self.orch, "logger", None)
        if lg:
            lg.info(f"[REMOTE] {verdict} from {ip}: {text[:80]}")

    # ---- HTTP server lifecycle ----
    def start(self) -> bool:
        """Start the LAN server in a daemon thread. Refuses (returns False) without a token."""
        if not self.token:
            lg = getattr(self.orch, "logger", None)
            if lg:
                lg.warn("[REMOTE] refused to start: JARVIS_REMOTE_TOKEN not set (no unauthenticated path).")
            return False
        if self._thread and self._thread.is_alive():
            return True
        rc = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):            # silence default stderr spam
                return

            def _send(self, status: int, payload: dict):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                # liveness only; leaks nothing, requires no auth
                if self.path == "/health":
                    self._send(200, {"ok": True})
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):
                if self.path != "/command":
                    self._send(404, {"error": "not found"})
                    return
                try:
                    n = int(self.headers.get("Content-Length", 0))
                    raw = self.rfile.read(n) if n else b""
                    data = json.loads(raw.decode("utf-8")) if raw else {}
                    text = data.get("text", "") or data.get("command", "")
                except Exception:
                    self._send(400, {"error": "bad request body"})
                    return
                ip = self.client_address[0] if self.client_address else "unknown"
                res = rc.handle_request(self.headers.get("Authorization"), text, ip)
                self._send(res["status"], {"reply": res["reply"]})

        self._httpd = ThreadingHTTPServer((self.host, self.port), _Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        lg = getattr(self.orch, "logger", None)
        if lg:
            lg.info(f"[REMOTE] LAN command server on {self.host}:{self.port} (token-gated). "
                    "Keep behind your router — do not port-forward.")
        return True

    def stop(self) -> None:
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
            self._httpd = None
