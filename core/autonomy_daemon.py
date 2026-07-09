"""Iron Man Mode — continuous, self-driving autonomy with safety rails.

This is the always-on layer that makes JARVIS feel like Tony Stark's JARVIS: hand it
standing goals and it works them on its own, in the background, one at a time — planning,
acting, verifying, reflecting, and improving itself between jobs — WITHOUT waiting to be
prompted each turn.

The frontier-agent lesson (AutoGPT drift, runaway cost, irreversible mistakes) is baked in
as hard rails:
  * It only ever advances ONE mission at a time, through the existing MissionControl loop,
    which already PAUSES the instant a step needs a risky/irreversible action and waits for
    the master's 'confirm'. The daemon detects that pause and stops advancing until cleared.
  * It is bounded: a per-day mission cap and a per-mission step budget, so it cannot loop
    forever or burn tokens uncontrollably.
  * It never invents high-risk work for itself. It works the master's queued goals; when the
    queue is empty it self-improves (Tier-1) and PROPOSES next goals as suggestions — it does
    not auto-execute things the master never asked for.
  * Everything it does is surfaced to the master through the normal alert buffer (HUD/voice).

So: maximally autonomous, but the owner is always on top and anything irreversible still
needs one 'yes'. That is the real, safe Iron Man JARVIS — not the fantasy that bricks itself.
"""
from __future__ import annotations

import json
import os
import threading
import time


class AutonomyDaemon:
    def __init__(self, orch, path: str = "memory/autonomy_goals.json"):
        self.orch = orch
        self.path = path
        cfg = (orch.settings.get("iron_man", {}) or {})
        self.interval = int(cfg.get("interval_seconds", 60))
        self.max_per_day = int(cfg.get("max_missions_per_day", 12))
        self.mission_budget = int(cfg.get("mission_budget", 12))
        self.improve_every = int(cfg.get("improve_every_missions", 4))
        self.running = False
        self.thread = None
        self._stop = threading.Event()
        self._day = time.strftime("%Y-%m-%d")
        self._missions_today = 0
        self._since_improve = 0
        self.last_result = ""

    # ---- goal queue (persisted) -----------------------------------------
    def _read(self) -> list:
        try:
            if os.path.exists(self.path):
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    def _write(self, goals: list):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(goals[-100:], f, indent=2)
        except Exception:
            pass

    def add_goal(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "Give me a goal to pursue, sir — e.g. 'add goal research the top 3 competitors and save a brief'."
        goals = self._read()
        goals.append({"goal": text, "status": "queued",
                      "added": time.strftime("%Y-%m-%dT%H:%M:%S"), "result": ""})
        self._write(goals)
        n = sum(1 for g in goals if g.get("status") == "queued")
        tail = " I'll work it autonomously." if self.running else " Say 'iron man mode on' and I'll start working it."
        return f"Added to the autonomy queue, sir ({n} goal(s) waiting).{tail}"

    def list_goals(self) -> str:
        goals = self._read()
        if not goals:
            return "No autonomy goals yet, sir. Add one with 'add goal <something>'."
        recent = goals[-15:]
        lines = ["Autonomy goals, sir:"]
        for g in recent:
            mark = {"queued": "•", "done": "done -", "blocked": "blocked -",
                    "working": "…"}.get(g.get("status"), "•")
            line = f"  {mark} {g.get('goal','')}"
            if g.get("status") == "done" and g.get("result"):
                line += f"  ({g['result'][:60]})"
            lines.append(line)
        q = sum(1 for g in goals if g.get("status") == "queued")
        lines.append(f"{q} still queued. Iron Man mode is {'ON' if self.running else 'OFF'}.")
        return "\n".join(lines)

    def _next_queued(self):
        goals = self._read()
        for g in goals:
            if g.get("status") == "queued":
                return goals, g
        return goals, None

    # ---- lifecycle -------------------------------------------------------
    def start(self) -> str:
        llm = self.orch.llm
        if not (llm and getattr(llm, "available", False)):
            return ("I need a brain online for autonomous work, sir — set a cloud key in .env or run Ollama, "
                    "then say 'iron man mode on'.")
        if self.running:
            return "Iron Man mode is already engaged, sir — I'm on it."
        self._stop.clear()
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="iron-man", daemon=True)
        self.thread.start()
        q = sum(1 for g in self._read() if g.get("status") == "queued")
        return (f"Iron Man mode engaged, sir. I'll work the {q} queued goal(s) autonomously, "
                f"checking in every {self.interval}s, pausing for your 'confirm' on anything irreversible. "
                "Say 'iron man mode off' to stand down.")

    def stop(self) -> str:
        if not self.running:
            return "Iron Man mode is already off, sir."
        self.running = False
        self._stop.set()
        return "Standing down from Iron Man mode, sir. Any half-finished mission is checkpointed."

    def status(self) -> str:
        goals = self._read()
        q = sum(1 for g in goals if g.get("status") == "queued")
        d = sum(1 for g in goals if g.get("status") == "done")
        b = sum(1 for g in goals if g.get("status") == "blocked")
        state = "ENGAGED" if self.running else "off"
        head = (f"Iron Man mode: {state}. Goals — {q} queued, {d} done, {b} blocked. "
                f"{self._missions_today}/{self.max_per_day} missions run today.")
        if self.orch.pending:
            head += " I'm holding for your 'confirm' on a pending action before I continue."
        if self.last_result:
            head += "\nLast: " + self.last_result[:160]
        return head

    # ---- the autonomous loop --------------------------------------------
    def _alert(self, text: str):
        try:
            with self.orch._alert_lock:
                self.orch.alerts.append("[Iron Man] " + text)
        except Exception:
            pass

    def _roll_day(self):
        today = time.strftime("%Y-%m-%d")
        if today != self._day:
            self._day = today
            self._missions_today = 0

    def _loop(self):
        # small initial delay so startup banter finishes first
        self._stop.wait(2)
        while self.running and not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:
                try:
                    self.orch.logger.error(f"iron-man tick failed: {e}")
                except Exception:
                    pass
            self._stop.wait(self.interval)

    def _tick(self):
        self._roll_day()
        o = self.orch

        # RAIL: never advance while a risky action awaits the master's confirm.
        if o.pending:
            return
        # RAIL: don't stack missions — let an active/paused mission finish or be resumed.
        if getattr(o.mission, "active", None):
            return
        # RAIL: per-day cap.
        if self._missions_today >= self.max_per_day:
            return

        goals, g = self._next_queued()
        if not g:
            # queue empty → self-improve once, then propose next goals (no auto-exec).
            self._idle_improve()
            return

        # work this goal autonomously through the safe mission loop
        g["status"] = "working"
        self._write(goals)
        self._missions_today += 1
        self._since_improve += 1
        self._alert(f"working: {g['goal']}")

        try:
            report = o.mission.run(g["goal"], budget=self.mission_budget) or "(no result)"
        except Exception as e:
            report = f"(failed: {e})"

        # re-read in case the queue changed while running, then update this goal
        goals = self._read()
        for gg in goals:
            if gg.get("goal") == g["goal"] and gg.get("status") == "working":
                if o.pending or (getattr(o.mission, "active", None)):
                    gg["status"] = "queued"   # paused for confirm → requeue, resume after
                    self._alert("paused for your confirm — say 'confirm' then I'll resume this goal.")
                else:
                    blocked = "blocked" in report.lower() and "0/" in report
                    gg["status"] = "blocked" if blocked else "done"
                    gg["result"] = report[:200]
                break
        self._write(goals)
        self.last_result = report
        # smarter autonomy: reflect on the finished mission and bank a reusable lesson
        if not o.pending and not getattr(o.mission, "active", None):
            self._reflect(g["goal"], report)
        self._alert(("paused: " if o.pending else "done: ") + report.split("\n", 1)[0][:160])

    def _reflect(self, goal: str, report: str):
        """Meta-reflection: extract one concrete lesson from the run and persist it,
        so future planning recalls what worked / failed (real learning-from-experience)."""
        o = self.orch
        llm = o.llm
        if not (llm and getattr(llm, "available", False)):
            return
        try:
            sysp = ("You are JARVIS reflecting on a just-finished autonomous mission. In ONE sentence under "
                    "25 words, state the single most useful lesson for doing this kind of task better next "
                    "time. No preamble.")
            lesson = llm.chat(sysp, f"Goal: {goal}\nOutcome:\n{report[:800]}\nLesson:")
            if not lesson:
                return
            lesson = lesson.strip()
            # bank it where future plans will see it: episodic memory + the persistent profile
            try:
                if hasattr(o.experience, "record"):
                    o.experience.record("lesson: " + goal, [lesson], "autonomy reflection")
            except Exception:
                pass
            try:
                o.memory.remember("autonomy_lessons", lesson)
            except Exception:
                pass
            self._alert("learned: " + lesson[:140])
        except Exception:
            pass

    def _idle_improve(self):
        """Queue empty: do Tier-1 self-improvement occasionally and propose next goals."""
        if self._since_improve < self.improve_every:
            return
        self._since_improve = 0
        o = self.orch
        # self-improve (advice only; installs/updates still need confirm)
        try:
            tip = o.improver.self_improve() if hasattr(o.improver, "self_improve") else ""
            if tip:
                self._alert("self-review: " + str(tip).split("\n", 1)[0][:160])
        except Exception:
            pass
        # propose the next highest-leverage goal (suggestion only, not executed)
        try:
            llm = o.llm
            if llm and getattr(llm, "available", False):
                sysp = ("You are JARVIS proposing the single highest-leverage next goal for your master's "
                        "standing work, given recent activity. Reply with ONE concrete goal in under 18 words, "
                        "no preamble.")
                recap = o.experience.recall("recent work") if hasattr(o.experience, "recall") else ""
                idea = llm.chat(sysp, "Recent context: " + str(recap)[:600] + "\nPropose one next goal:")
                if idea:
                    self._alert("suggested next goal (say 'add goal …' to approve): " + idea.strip()[:160])
        except Exception:
            pass
