"""Proactive Advisor — the 'JARVIS speaks up on his own' layer.

Movie JARVIS doesn't only answer; he volunteers the right remark at the right moment.
This background advisor periodically observes the master's CONTEXT (the current browser
tab, time of day) and, when something genuinely useful comes to mind, pushes a short
spoken suggestion through the normal alert buffer (HUD/voice) — unprompted.

Anti-Clippy guardrails (so it helps instead of nagging):
  * Frequency cap — at most one suggestion per `min_gap_seconds` (default 5 min).
  * Change-gated — only reconsiders when the context actually changed (new tab/URL),
    never re-comments on the same page.
  * NO_SUGGESTION sentinel — the model is told to stay silent unless it has something
    genuinely worth saying; silence is the default, not chatter.
  * Read-only — it observes and advises; it never acts. (Acting stays with the master /
    Mission Control / Iron Man Mode, which keep their own confirm gates.)
"""
from __future__ import annotations

import threading
import time


class ProactiveAdvisor:
    def __init__(self, orch):
        self.orch = orch
        cfg = (orch.settings.get("proactive_advice", {}) or {})
        self.interval = int(cfg.get("interval_seconds", 90))
        self.min_gap = int(cfg.get("min_gap_seconds", 300))
        self.running = False
        self.thread = None
        self._stop = threading.Event()
        self._last_suggest = 0.0
        self._last_sig = None
        self.last_tip = ""

    # ---- lifecycle ----
    def start(self) -> str:
        llm = self.orch.llm
        if not (llm and getattr(llm, "available", False)):
            return "I need a brain online to offer proactive advice, sir — set a key or run Ollama."
        if self.running:
            return "I'm already keeping an eye out and will speak up when something's worth saying, sir."
        self._stop.clear()
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="proactive-advisor", daemon=True)
        self.thread.start()
        return ("Proactive advice engaged, sir. I'll watch your context and volunteer a suggestion when "
                "it's genuinely useful — no chatter. Say 'proactive off' to silence it.")

    def stop(self) -> str:
        if not self.running:
            return "Proactive advice is already off, sir."
        self.running = False
        self._stop.set()
        return "I'll hold my tongue unless you ask, sir — proactive advice off."

    def status(self) -> str:
        state = "ON" if self.running else "off"
        head = f"Proactive advice: {state} (at most one tip every {self.min_gap // 60} min)."
        if self.last_tip:
            head += "\nLast tip: " + self.last_tip[:160]
        return head

    # ---- loop ----
    def _alert(self, text: str):
        try:
            with self.orch._alert_lock:
                self.orch.alerts.append("[JARVIS] " + text)
        except Exception:
            pass

    def _loop(self):
        self._stop.wait(3)
        while self.running and not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:
                try:
                    self.orch.logger.error(f"proactive tick failed: {e}")
                except Exception:
                    pass
            self._stop.wait(self.interval)

    def _context(self):
        """Best-effort read of what the master is doing right now (current tab)."""
        try:
            br = self.orch.tools.get("browser_root")
            if br:
                fb = br.read_current_page()
                if fb.get("started"):
                    return {"url": fb.get("url", ""), "title": fb.get("title", ""),
                            "text": (fb.get("text") or "")[:3000]}
        except Exception:
            pass
        return None

    def _tick(self):
        # frequency cap
        if time.time() - self._last_suggest < self.min_gap:
            return
        ctx = self._context()
        if not ctx:
            return                                  # nothing observable → stay silent
        sig = (ctx.get("url", "") or ctx.get("title", ""))[:200]
        if not sig or sig == self._last_sig:
            return                                  # same page as last time → don't repeat
        self._last_sig = sig

        llm = self.orch.llm
        if not (llm and getattr(llm, "available", False)):
            return
        sysp = (self.orch.system_prompt +
                "\n\nYou are observing the master's current screen context UNPROMPTED. If — and only if — "
                "you have a genuinely useful, specific suggestion, advice, or insight for what he's looking "
                "at, say it in ONE or two short spoken sentences as his butler. If nothing is truly worth "
                "interrupting him for, reply with exactly NO_SUGGESTION and nothing else.")
        user = (f"Current tab: {ctx.get('title','')} ({ctx.get('url','')})\n"
                f"Visible text:\n{ctx.get('text','')}\n\nYour proactive remark (or NO_SUGGESTION):")
        try:
            tip = llm.chat(sysp, user)
        except Exception:
            return
        if not tip:
            return
        tip = tip.strip()
        if "NO_SUGGESTION" in tip or len(tip) < 8:
            return
        self._last_suggest = time.time()
        self.last_tip = tip
        self._alert(tip)
