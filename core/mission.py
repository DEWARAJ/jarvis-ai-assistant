"""Mission Control — continuous autonomous mode (Devin / AutoGPT style, but safe).

Give JARVIS a big goal and it will:
  1) decompose it into subtasks,
  2) work them one at a time through the ReAct agent loop (each up to several micro-steps),
  3) ask a controller after each step whether the goal is done and SELF-SPAWN new subtasks
     it discovers along the way,
  4) checkpoint progress and keep a persistent mission log,
  5) and — the safe difference from AutoGPT — PAUSE the moment a step needs a risky action,
     wait for the master's 'confirm', then 'continue mission' to resume.

Bounded by a step budget so it can't loop forever or burn tokens uncontrollably.
"""
from __future__ import annotations
import os, json, time
from core import reliability as _rel


class MissionControl:
    def __init__(self, orch, path: str = "memory/missions.json"):
        self.orch = orch
        self.path = path
        self.active = None  # current mission state dict, or None

    # ---- controller (decides completion + spawns subtasks) ----
    def _assess(self, goal: str, done: list, todo: list) -> dict:
        llm = self.orch.llm
        if not (llm and getattr(llm, "available", False)):
            return {"complete": False, "new_subtasks": []}
        sysp = ("You are JARVIS's mission controller. Decide whether the overall goal is now achieved, and "
                "propose any NEW subtasks you've realised are needed (only genuinely new, concrete ones). "
                'Reply with ONLY JSON: {"complete": true/false, "new_subtasks": ["..."], "note": "..."}')
        user = ("Goal: " + goal + "\nDone so far: " +
                ("; ".join(d["task"] + ("(ok)" if d["ok"] else "(blocked)") for d in done) or "nothing") +
                "\nStill queued: " + ("; ".join(todo) or "nothing"))
        out = llm.chat(sysp, user)
        if not out:
            return {"complete": False, "new_subtasks": []}
        import re
        data = None
        try:
            data = json.loads(out)
        except Exception:
            m = re.search(r"\{.*\}", out, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception:
                    data = None
        return data if isinstance(data, dict) else {"complete": False, "new_subtasks": []}

    # ---- drive loop ----
    def _drive(self) -> str:
        m = self.active
        o = self.orch
        o.live.begin("mission", "autonomous")
        while m["todo"] and m["budget"] > 0:
            sub = m["todo"].pop(0)
            m["budget"] -= 1
            o.live.step(f"[{len(m['done']) + 1}] {sub}")
            out = o.agentic.act_loop(sub) or "(no result)"
            ok = not _rel.looks_failed(out)
            m["done"].append({"task": sub, "ok": ok})
            m["log"].append(sub + " -> " + ("ok" if ok else "blocked"))

            # SAFE PAUSE: a step queued a risky action awaiting the master's confirmation
            if o.pending:
                self._persist("paused")
                return self._render(paused=True)

            assess = self._assess(m["goal"], m["done"], m["todo"])
            if assess.get("complete"):
                m["todo"] = []
                break
            for ns in (assess.get("new_subtasks") or [])[:3]:
                ns = str(ns).strip()
                if (ns and ns not in m["todo"] and ns not in [d["task"] for d in m["done"]]
                        and m["spawned"] < 8 and (len(m["done"]) + len(m["todo"])) < m["limit"]):
                    m["todo"].append(ns)
                    m["spawned"] += 1
        o.live.done("mission complete", True)
        report = self._render(paused=False)
        try:
            o.experience.record(m["goal"], [d["task"] for d in m["done"]], self._recap())
        except Exception:
            pass
        self._persist("complete")
        self.active = None
        return report

    # ---- public API ----
    def run(self, goal: str, budget: int = 16):
        goal = (goal or "").strip()
        if not goal:
            return "Give me a mission, sir — say 'mission <goal>' and I'll plan it and work it autonomously."
        llm = self.orch.llm
        if not (llm and getattr(llm, "available", False)):
            return None
        recall = self.orch.experience.recall(goal)
        todo = self.orch.planner._decompose(goal, recall)
        self.active = {"goal": goal, "todo": list(todo), "done": [], "log": [],
                       "budget": budget, "limit": budget, "spawned": 0,
                       "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
        return self._drive()

    def resume(self):
        if not self.active:
            return "There's no mission to resume, sir."
        if self.orch.pending:
            return "An action is still awaiting your 'confirm', sir — approve or cancel it, then say 'continue mission'."
        return self._drive()

    def abort(self):
        if not self.active:
            return "There's no active mission, sir."
        g = self.active["goal"]
        self._persist("aborted")
        self.active = None
        return "Mission aborted, sir: " + g

    def status(self):
        if not self.active:
            return "No active mission, sir."
        m = self.active
        return (f"Mission: {m['goal']}. Completed {len(m['done'])} step(s), {len(m['todo'])} queued, "
                f"{m['budget']} of {m['limit']} budget remaining.")

    # ---- helpers ----
    def _recap(self) -> str:
        m = self.active
        ok = sum(1 for d in m["done"] if d["ok"])
        return f"{ok}/{len(m['done'])} steps completed."

    def _render(self, paused: bool) -> str:
        m = self.active
        head = "Mission paused, sir." if paused else "Mission complete, sir."
        if not paused and m["todo"] and m["budget"] <= 0:
            head = "Mission reached its step budget, sir."
        lines = [head, "Goal: " + m["goal"]]
        if m["done"]:
            lines.append("Steps:")
            for d in m["done"]:
                lines.append(("  done - " if d["ok"] else "  blocked - ") + d["task"])
        ok = sum(1 for d in m["done"] if d["ok"])
        lines.append(f"{ok}/{len(m['done'])} steps completed; {len(m['todo'])} still queued.")
        if paused:
            lines.append("An action needs your approval before I continue. Say 'confirm' to allow it "
                         "(or 'cancel'), then 'continue mission'.")
        return "\n".join(lines)

    def _persist(self, status: str):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            log = []
            if os.path.exists(self.path):
                try:
                    with open(self.path, encoding="utf-8") as f:
                        log = json.load(f)
                except Exception:
                    log = []
            m = self.active or {}
            log.append({"goal": m.get("goal"), "status": status, "log": m.get("log", []),
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(log[-50:], f, indent=2)
        except Exception:
            pass
