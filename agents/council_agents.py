"""Council member sub-agents — FRIDAY, TRON, IRA, MYTHOS.

These make the council members real, registered, individually-callable agents (so they
appear in the Sub-systems panel and respond on their own, just like ULTRON). They reuse
the same personas as core/council.py. Each ADVISES/REVIEWS only — no agent executes
side-effecting actions; that stays behind the orchestrator's safety + permission gates.
"""
from __future__ import annotations

from agents.base_agent import BaseAgent
from core.council import FRIDAY_SYS, TRON_SYS, IRA_SYS, MYTHOS_SYS


class _PersonaAgent(BaseAgent):
    """Shared base: answer through a fixed persona via the LLM, degrade honestly."""
    SYSTEM = ""
    offline_msg = "The reasoning core is offline, sir — enable a brain and ask me again."

    def _answer(self, user: str) -> str:
        llm = self.llm
        if llm and getattr(llm, "available", False):
            try:
                ans = llm.chat(self.SYSTEM, user)
                if ans:
                    return ans
            except Exception:
                pass
        return self.offline_msg

    def run(self, action: str, args: str = "", plan=None) -> str:
        topic = (args or "").strip()
        if not topic:
            return f"[{self.name}] Give me something to work on, sir."
        return self._answer(topic)


class FridayAgent(_PersonaAgent):
    role = "Live research & web intelligence; verifies facts and cites sources. Advises only."
    risk = "low"
    SYSTEM = FRIDAY_SYS

    def run(self, action: str, args: str = "", plan=None) -> str:
        topic = (args or "").strip()
        if not topic:
            return "[FRIDAY] Name a topic, sir, and I'll research it across the live web."
        evidence = ""
        web = self.tool("web")
        if web:
            try:
                _s, results = web.search(topic, n=5)
                evidence = results or ""
            except Exception:
                evidence = ""
        user = ("Research and brief your master on: " + topic + "\n\n" +
                ("LIVE WEB EVIDENCE (ground it, cite the best source):\n" + evidence
                 if evidence else "No live web evidence available — say so and advise from general knowledge."))
        return self._answer(user)


class TronAgent(_PersonaAgent):
    role = "Builder-debugger; assesses how to implement, what breaks, how to verify. Advises only."
    risk = "low"
    SYSTEM = TRON_SYS


class IraAgent(_PersonaAgent):
    role = "Security, safety & quality control with veto; classifies risk SAFE-to-CRITICAL."
    risk = "low"
    SYSTEM = IRA_SYS

    def run(self, action: str, args: str = "", plan=None) -> str:
        topic = (args or "").strip()
        if not topic:
            return "[IRA] Give me the action or output to review, sir, and I'll classify the risk."
        guard = ""
        try:
            safety = self.context.get("safety")
            if safety:
                rv = safety.review(topic, topic)
                guard = ("SafetyGuard: " + ("allowed" if rv.allowed else "blocked") +
                         ((" — " + "; ".join(rv.warnings)) if getattr(rv, "warnings", None) else ""))
        except Exception:
            pass
        return self._answer((guard + "\n\n" if guard else "") +
                            "Classify the risk and give your safety/quality verdict on: " + topic)


class MythosAgent(_PersonaAgent):
    role = "Creativity, strategy & uniqueness; elevates work from correct to outstanding."
    risk = "low"
    SYSTEM = MYTHOS_SYS
