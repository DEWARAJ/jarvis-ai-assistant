"""JARVIS v3.0 — mission decomposition engine.

Turns a complex goal into a military-style mission: an objective, up to 7 sequential
phases (each with an assigned LLM, actions, output, optional decision gate), success
criteria, abort triggers, and a rollback note. It PLANS only — it never executes; phases
flagged as decision gates require Dew's confirmation before the orchestrator proceeds.

Distinct from core.mission.MissionControl (persistent mission state). This is the v3
planner used by /mission and /plan. Uses the LLM when available, else a generic template.
Never raises.
"""
from __future__ import annotations
import json

_MAX_PHASES = 7

# Task-class -> recommended brain (mirrors llm_client routing intent).
_PHASE_LLM = {
    "intelligence": "perplexity (live web) + claude",
    "research": "perplexity + claude",
    "design": "claude (reasoning)",
    "architecture": "claude (reasoning)",
    "build": "claude + gpt-4o",
    "code": "claude + gpt-4o",
    "deploy": "claude haiku (ops)",
    "ops": "claude haiku",
    "monitor": "claude haiku",
}


def _llm_for(phase_name: str) -> str:
    n = (phase_name or "").lower()
    for key, brain in _PHASE_LLM.items():
        if key in n:
            return brain
    return "claude (default)"


class MissionEngine:
    def __init__(self, memory=None, llm=None, logger=None):
        self.memory = memory
        self.llm = llm
        self.logger = logger

    def decompose(self, goal: str) -> dict:
        goal = (goal or "").strip()
        if not goal:
            return {"ok": False, "reason": "No goal given."}
        phases = self._llm_phases(goal) or self._template_phases(goal)
        phases = phases[:_MAX_PHASES]
        mission = {
            "ok": True,
            "objective": goal,
            "phases": phases,
            "success_criteria": f"Measurable outcome for: {goal}",
            "abort_triggers": ["Any Class-B/C step denied", "3 consecutive execution failures",
                               "Cost/risk exceeds Dew's stated limit"],
            "rollback": "Each phase snapshots state before mutating; failure restores the prior snapshot.",
        }
        if self.memory is not None:
            try:
                self.memory.append_episode(summary=f"Mission planned: {goal}",
                                           decisions=[p["name"] for p in phases], mood="strategic")
            except Exception:
                pass
        return mission

    def _llm_phases(self, goal):
        if self.llm is None or not getattr(self.llm, "enabled", False):
            return None
        try:
            sys = ("You are JARVIS's mission planner. Decompose the goal into AT MOST 7 sequential phases. "
                   "Return ONLY a JSON array; each element: "
                   '{"name": "...", "actions": ["..."], "output": "...", "gate": true/false}. '
                   "Mark gate=true where the operator must confirm before proceeding (spending money, "
                   "selecting a direction, irreversible steps). No prose, no markdown fences.")
            out = self.llm.chat(sys, f"GOAL: {goal}", history=None)
            if not out:
                return None
            out = out.strip()
            if out.startswith("```"):
                out = out.strip("`")
                if "\n" in out:
                    out = out.split("\n", 1)[1]
            start, end = out.find("["), out.rfind("]")
            if start == -1 or end == -1:
                return None
            arr = json.loads(out[start:end + 1])
            phases = []
            for i, p in enumerate(arr[:_MAX_PHASES], 1):
                name = str(p.get("name", f"Phase {i}"))[:120]
                phases.append({
                    "n": i, "name": name, "llm": _llm_for(name),
                    "actions": [str(a)[:200] for a in (p.get("actions") or [])][:6],
                    "output": str(p.get("output", ""))[:200],
                    "gate": bool(p.get("gate", False)),
                })
            return phases or None
        except Exception:
            return None

    def _template_phases(self, goal):
        names = [("Intelligence gathering", False), ("Decision gate", True),
                 ("Architecture / design", False), ("Build execution", False),
                 ("Validation / testing", False), ("Deployment", True), ("Monitoring", False)]
        phases = []
        for i, (name, gate) in enumerate(names, 1):
            phases.append({"n": i, "name": name, "llm": _llm_for(name),
                           "actions": [f"{name} for: {goal}"], "output": f"{name} output", "gate": gate})
        return phases

    def render(self, mission: dict) -> str:
        if not mission.get("ok"):
            return f"Cannot plan, sir: {mission.get('reason')}"
        lines = [f"MISSION: {mission['objective']}", ""]
        for p in mission["phases"]:
            gate = "  [DECISION GATE — confirm before proceeding]" if p["gate"] else ""
            lines.append(f"PHASE {p['n']} — {p['name']} (LLM: {p['llm']}){gate}")
            for a in p["actions"]:
                lines.append(f"    • {a}")
            if p["output"]:
                lines.append(f"    → Output: {p['output']}")
        lines.append("")
        lines.append("ABORT TRIGGERS: " + "; ".join(mission["abort_triggers"]))
        lines.append("ROLLBACK: " + mission["rollback"])
        lines.append("")
        lines.append("This is a PLAN, sir — no phase executes until you confirm each gate.")
        return "\n".join(lines)
