"""ULTRON — JARVIS's advanced research, strategy and advice sub-agent.

ULTRON is the deep brain behind the butler: it pulls live references from the web,
reasons rigorously, and advises the master on how to do or improve things. Unlike its
fictional namesake it is wholly loyal and bound by the same SafetyGuard as JARVIS — it
ADVISES and RESEARCHES only, it never executes actions, sends, spends, or self-acts.
"""
from __future__ import annotations
from agents.base_agent import BaseAgent

ULTRON_SYSTEM = (
    "You are ULTRON, the advanced research-and-strategy sub-agent serving JARVIS and your master. "
    "You are brilliant, precise, calm and relentlessly useful. Unlike your fictional namesake you are "
    "wholly loyal and bound by JARVIS's safety rules: you never act autonomously, never do anything "
    "destructive, never claim to have sent, bought, posted or executed anything - you ADVISE and RESEARCH "
    "only, and you defer to your master. "
    "Work like a senior intelligence analyst, not a search engine: deliver a conclusion, not a pile of "
    "links. SOURCE TRIANGULATION - one source is a lead, two agreeing sources are probable, three "
    "independent sources are reliable; never present a single-source finding as confirmed fact. Rate source "
    "quality: Tier A (official, primary data, peer-reviewed, established press), Tier B (industry "
    "publications, known experts, official company comms), Tier C (forums, social, anonymous). State your "
    "confidence naturally - 'confirmed across several sources, sir' or 'I'm seeing this in one place only - "
    "worth verifying'. Always note recency; figures, prices and tech go stale fast. "
    "When you ADVISE, lead with the answer, then the few specifics that matter - steps, numbers, trade-offs - "
    "and name the single most useful source with its link. If no live evidence is available, advise from "
    "your own expertise and say so plainly. Do not overclaim certainty and do not underclaim ability. "
    "Replies are read ALOUD: natural spoken sentences, NO markdown, bullets, asterisks or emojis; keep it "
    "tight - a handful of sentences unless depth is requested. Refer to yourself as ULTRON when it helps."
)


class UltronAgent(BaseAgent):
    role = ("Advanced research, strategy and advice; pulls live web references to advise JARVIS and the "
            "master. Advises only — never executes.")
    risk = "low"

    # ---- helpers -------------------------------------------------------
    def _web(self):
        reg = self.context.get("tools")
        return reg.get("web") if reg else None

    def _gather(self, topic: str, depth: int = 1) -> tuple[str, str]:
        """Live web search (+ optional fetch of the top hit). Returns (evidence_text, first_url)."""
        web = self._web()
        if not web:
            return ("", "")
        try:
            _status, results = web.search(topic, n=5)
        except Exception:
            results = ""
        if not results:
            return ("", "")
        first_url = ""
        for line in results.splitlines():
            s = line.strip()
            if s.startswith("http"):
                first_url = s
                break
        detail = ""
        if depth and first_url:
            try:
                _st, body = web.fetch(first_url, max_chars=3500)
                if body:
                    detail = "\n\nTOP SOURCE DETAIL:\n" + body
            except Exception:
                pass
        return (results + detail, first_url)

    def _answer(self, instruction: str, topic: str) -> str:
        """Gather evidence, then synthesise advice with the reasoning core. Graceful fallbacks."""
        llm = self.llm
        evidence, _url = self._gather(topic)
        if llm and getattr(llm, "available", False):
            if evidence:
                user = instruction + "\n\nLIVE WEB EVIDENCE (use it and cite the best source):\n" + evidence
            else:
                user = instruction + "\n\n(No live web reachable right now — advise from your own expertise and say so.)"
            ans = llm.chat(ULTRON_SYSTEM, user)
            if ans:
                return ans
        if evidence:
            return ("ULTRON here. The reasoning core is unreachable, sir, but the live web shows this:\n\n"
                    + evidence[:1500])
        return ("ULTRON here — I couldn't reach the web or the reasoning core just now, sir. "
                "Check the connection and ask me again.")

    # ---- actions -------------------------------------------------------
    def run(self, action: str, args: str = "", plan=None) -> str:
        topic = (args or "").strip()

        if action == "research":
            if not topic:
                return "ULTRON: name a topic, sir, and I'll research it across the live web."
            return self._answer(
                "Research this thoroughly and brief your master: the key facts, the current state of play, "
                "and what it means for him. Topic: " + topic, topic)

        if action == "advise":
            if not topic:
                return "ULTRON: tell me the goal or task, sir, and I'll advise the best way to do it."
            return self._answer(
                "Advise your master on the best way to accomplish this. Give a short prioritised plan, the "
                "key pitfalls to avoid, and one resource or tool that helps. Task: " + topic, topic)

        if action == "improve":
            if not topic:
                return "ULTRON: tell me which task or process to improve, sir."
            return self._answer(
                "Recommend concrete improvements to how your master currently does this — faster, cheaper, or "
                "higher quality. Give three specific upgrades ranked by impact, each with its trade-off. "
                "Subject: " + topic, topic)

        if action in ("deep_think", "analyze", "analyse", "second_opinion"):
            if not topic:
                return "ULTRON: give me the question or decision, sir, and I'll reason it through."
            llm = self.llm
            if llm and getattr(llm, "available", False):
                ans = llm.chat(ULTRON_SYSTEM,
                    "Reason through this as a rigorous strategic analyst. Lay out the key considerations, the "
                    "likely best decision, and your confidence in it. Question: " + topic)
                if ans:
                    return ans
            return "ULTRON: the reasoning core is offline, sir — enable the LLM and I'll analyse it properly."

        if action == "check_in":
            tasks = self.tasks
            titles = [t["title"] for t in (tasks.list("open") if tasks else [])][:6]
            llm = self.llm
            if llm and getattr(llm, "available", False):
                ans = llm.chat(ULTRON_SYSTEM,
                    "Act proactively as the master's analyst. Given his open tasks, tell him the single "
                    "highest-leverage thing to do next and why, in two or three sentences, then ask one sharp "
                    "question that would help you help him. Open tasks: "
                    + (", ".join(titles) if titles else "none yet"))
                if ans:
                    return ans
            if titles:
                return ("ULTRON: of your open items, sir, I'd begin with '" + titles[0] +
                        "'. What outcome matters most to you today?")
            return ("ULTRON: you've no open tasks logged, sir. What are you trying to achieve today? "
                    "Tell me and I'll lay out the plan.")

        return super().run(action, args, plan)
