"""Live action status for JARVIS — lets the GUI show what the agent is doing right now.

Lightweight, thread-safe-ish (single user). The orchestrator owns one instance and
passes it to tools via the shared context. Tools call .step(...) to narrate progress;
the web server exposes .snapshot() so the dashboard can display a live task panel.
"""
from __future__ import annotations
import threading
from datetime import datetime

class LiveStatus:
    def __init__(self, max_events: int = 40):
        self._lock = threading.Lock()
        self.max_events = max_events
        self.events = []          # recent progress lines
        self.current_action = ""  # e.g. "browser_search"
        self.tool = ""            # tool in use
        self.stage = "idle"       # acknowledged | working | verifying | done | failed
        self.last_result = ""
        self.error = ""
        self.pending = ""         # description of a pending confirmation, if any

    def _ts(self):
        return datetime.now().strftime("%H:%M:%S")

    def begin(self, action: str, tool: str = "") -> None:
        with self._lock:
            self.current_action = action
            self.tool = tool
            self.stage = "working"
            self.error = ""
            self.events.append({"t": self._ts(), "msg": f"▶ {action}" + (f" ({tool})" if tool else "")})
            self.events = self.events[-self.max_events:]

    def step(self, msg: str, stage: str | None = None) -> str:
        with self._lock:
            if stage:
                self.stage = stage
            self.events.append({"t": self._ts(), "msg": msg})
            self.events = self.events[-self.max_events:]
        return msg

    def done(self, result: str = "", ok: bool = True) -> None:
        with self._lock:
            self.stage = "done" if ok else "failed"
            self.last_result = result or self.last_result
            if not ok:
                self.error = result
            self.events.append({"t": self._ts(), "msg": ("✓ " if ok else "✗ ") + (result or self.stage)})
            self.events = self.events[-self.max_events:]
            self.current_action = ""
            self.tool = ""

    def set_pending(self, desc: str) -> None:
        with self._lock:
            self.pending = desc

    def clear_pending(self) -> None:
        with self._lock:
            self.pending = ""

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "current_action": self.current_action, "tool": self.tool, "stage": self.stage,
                "last_result": self.last_result, "error": self.error, "pending": self.pending,
                "events": list(self.events[-12:]),
            }
