"""Long-horizon planner — hierarchical goal decomposition with verify-and-repair.

Breaks a large goal into ordered subgoals, runs each through the ReAct agent loop, checks
the outcome, makes one repair attempt on failure, then records the episode to memory so
JARVIS recalls similar past tasks next time. This is the 2026 frontier pattern: a planner
that decomposes, verifies at execution time, and learns from experience.
"""
from __future__ import annotations
import json, re
from core import reliability as _rel


class Planner:
    def __init__(self, orch):
        self.orch = orch

    def _system(self) -> str:
        return ("You are JARVIS's planner. Break the master's goal into 2 to 6 concrete, ordered subgoals, "
                "each a single actionable step JARVIS can carry out (open/search/read/write/click/verify). "
                'Reply with ONLY JSON: {"subgoals": ["...", "..."]}. Concrete, minimal, in order.')

    def _decompose(self, goal: str, recall: list) -> list:
        llm = self.orch.llm
        ctx = ""
        if recall:
            ctx = "\n\nSimilar past tasks for reference:\n" + "\n".join(
                "- " + r.get("goal", "") + " -> " + (r.get("outcome", "")[:120]) for r in recall)
        out = llm.chat(self._system(), "Goal: " + goal + ctx + "\n\nJSON only.")
        data = None
        if out:
            try:
                data = json.loads(out)
            except Exception:
                m = re.search(r"\{.*\}", out, re.DOTALL)
                if m:
                    try:
                        data = json.loads(m.group(0))
                    except Exception:
                        data = None
        subs = data.get("subgoals") if isinstance(data, dict) else None
        if not isinstance(subs, list) or not subs:
            return [goal]
        clean = [str(s).strip() for s in subs if str(s).strip()][:6]
        return clean or [goal]

    def run(self, goal: str):
        goal = (goal or "").strip()
        if not goal:
            return "What's the project, sir? Tell me the goal and I'll plan it out and execute it."
        llm = self.orch.llm
        if not (llm and getattr(llm, "available", False)):
            return None  # caller falls back

        recall = self.orch.experience.recall(goal)
        self.orch.live.begin("planner", "plan")
        self.orch.live.step("Decomposing the goal into subgoals…")
        subgoals = self._decompose(goal, recall)

        results = []
        for i, sg in enumerate(subgoals):
            self.orch.live.step(f"Subgoal {i+1}/{len(subgoals)}: {sg}")
            out = self.orch.agentic.act_loop(sg) or "(no result)"
            ok = not _rel.looks_failed(out)
            if not ok:
                self.orch.live.step(f"Repairing subgoal {i+1}…")
                alt = self.orch.agentic.act_loop("The previous attempt failed; achieve this another way: " + sg)
                if alt and not _rel.looks_failed(alt):
                    out, ok = alt, True
            results.append((sg, ok, out))
        self.orch.live.done("plan complete", True)

        done = sum(1 for _, ok, _ in results if ok)
        recap = f"{done} of {len(results)} subgoals completed."
        self.orch.experience.record(goal, subgoals, recap)

        lines = ["Plan, sir:"] + [f"  {i+1}. {s}" for i, s in enumerate(subgoals)]
        report = ["Here's how it went:"] + [("  " + ("done" if ok else "blocked") + " - " + sg)
                                            for sg, ok, _ in results]
        wrap = ""
        if recall:
            wrap = "\n\n(I drew on " + str(len(recall)) + " similar past task(s) to plan this.)"
        try:
            w = llm.chat(self.orch.system_prompt,
                         "In one short butler sentence, summarise this for the master: " + recap +
                         " The goal was: " + goal)
            if w:
                wrap = "\n\n" + w + wrap
        except Exception:
            pass
        return "\n".join(lines) + "\n\n" + "\n".join(report) + "\n\n" + recap + wrap
