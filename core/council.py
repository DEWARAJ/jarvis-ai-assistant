"""The Council — JARVIS's multi-agent review board.

For important tasks JARVIS convenes a council of specialist personas, each with a
distinct job, then synthesises their findings into a single final decision. This is
the "expert council" pattern: members do NOT rubber-stamp each other — FRIDAY checks
truth, TRON checks execution, ULTRON attacks weakness, IRA checks safety (with veto),
MYTHOS pushes for excellence, and JARVIS decides.

Design notes / honesty:
  * Each member is one bounded LLM call with its own system persona, run sequentially
    so later members see earlier findings. No runaway loops, no token blowup.
  * FRIDAY uses the live `web` tool when available; if not, it says so plainly and
    never fabricates web results.
  * IRA reuses the real SafetyGuard risk classification — it is not a vibe; HIGH/CRITICAL
    sets `approval_required`, which JARVIS surfaces so the master must approve.
  * Every member's contribution is written to the audit log via the orchestrator logger.
  * Degrades honestly: no LLM → returns a clear "reasoning core offline" council notice.
"""
from __future__ import annotations

import time


FRIDAY_SYS = (
    "You are FRIDAY, JARVIS's live-research and intelligence officer. Verify facts, gather current "
    "references, compare sources, and separate fact from opinion. Triangulate: one source is a lead, "
    "two agreeing are probable, three independent are reliable. Rate confidence (high/medium/low) and "
    "note recency. If you were given live web evidence, ground your summary in it and name the best source. "
    "If no live evidence was provided, say 'Live web not consulted for this' and advise from general "
    "knowledge without inventing specifics. Be concise: a tight briefing, not a pile of links.")
TRON_SYS = (
    "You are TRON, JARVIS's builder-debugger engineer. Assess HOW to actually execute or implement the "
    "task: the concrete steps, the files/tools/commands involved, what could break, and how you'd verify "
    "success. Flag anything technically risky or irreversible. If it's not a build task, give the practical "
    "execution path. Be specific and buildable, not hand-wavy.")
ULTRON_SYS = (
    "You are ULTRON, JARVIS's critic and red-team. Your job is to ATTACK the plan, never to agree. Find the "
    "weakest assumption, the hidden risk, the missing evidence, the overconfidence, the failure mode. Argue "
    "the opposite case. List concrete objections, each with why it matters. End with the single biggest flaw "
    "that must be fixed. Do not soften it.")
IRA_SYS = (
    "You are IRA, JARVIS's safety and quality controller with VETO power. Judge: is this safe, reversible, "
    "legal, privacy-respecting, and free of financial/account risk? Classify risk as SAFE / LOW / MEDIUM / "
    "HIGH / CRITICAL. Call out anything destructive, irreversible, money-spending, credential-touching, or "
    "rule-violating. State clearly whether master approval is required and why. Be strict; err toward caution.")
MYTHOS_SYS = (
    "You are MYTHOS, JARVIS's creativity and strategy agent. Take the work past 'merely correct' to "
    "outstanding: a sharper approach, a more elegant solution, a premium touch, a non-obvious improvement. "
    "Give one or two high-leverage upgrades that make the result genuinely better — without breaking "
    "correctness or safety. Be original, not gimmicky.")
JARVIS_SYS = (
    "You are JARVIS, the master orchestrator and the master's loyal chief of staff. You have just heard your "
    "council. Synthesise their findings into ONE decision for your master. Resolve disagreements and say why. "
    "If IRA flagged HIGH or CRITICAL risk, do NOT proceed — require the master's approval first. Be honest: if "
    "the request is unwise, say so and offer the better path. Lead with the answer. Address him as 'sir'.")


class Council:
    def __init__(self, orch):
        self.orch = orch

    # ---- helpers --------------------------------------------------------
    def _llm_ok(self) -> bool:
        return bool(self.orch.llm and getattr(self.orch.llm, "available", False))

    def _ask(self, system: str, user: str) -> str:
        try:
            return (self.orch.llm.chat(system, user) or "").strip()
        except Exception as e:
            return f"(unavailable: {e})"

    def _friday_evidence(self, task: str) -> tuple[str, bool]:
        """Live web evidence for FRIDAY. Returns (evidence, web_used)."""
        try:
            reg = self.orch.tools
            web = reg.get("web") if reg else None
            if not web:
                return ("", False)
            _status, results = web.search(task, n=5)
            return ((results or ""), bool(results))
        except Exception:
            return ("", False)

    def _ira_risk(self, task: str) -> str:
        """Reuse the real SafetyGuard to ground IRA's risk read, not just an opinion."""
        try:
            review = self.orch.safety.review(task, task)
            return ("allowed" if review.allowed else "blocked") + (
                (" — " + "; ".join(review.warnings)) if getattr(review, "warnings", None) else "")
        except Exception:
            return "unknown"

    def _audit(self, member: str, text: str):
        try:
            self.orch.logger.info(f"council:{member} :: {text[:160]}")
        except Exception:
            pass

    # ---- main -----------------------------------------------------------
    def review(self, task: str) -> str:
        task = (task or "").strip()
        if not task:
            return ("Convene the council on what, sir? Say 'council <goal>' and I'll have FRIDAY, TRON, "
                    "ULTRON, IRA and MYTHOS weigh in before I decide.")
        if not self._llm_ok():
            return ("The reasoning core is offline, sir — the council needs the LLM brain. Enable a key "
                    "(or Ollama) and convene me again.")

        if hasattr(self.orch, "live"):
            try: self.orch.live.begin("council", "multi-agent")
            except Exception: pass
        started = time.strftime("%H:%M:%S")

        # 1) FRIDAY — research (live web grounded)
        ev, web_used = self._friday_evidence(task)
        fri_user = ("Task for the council: " + task + "\n\n" +
                    ("LIVE WEB EVIDENCE (ground your briefing in this, cite the best source):\n" + ev
                     if web_used else "No live web evidence was available for this run."))
        friday = self._ask(FRIDAY_SYS, fri_user); self._audit("FRIDAY", friday)

        ctx = f"TASK: {task}\n\nFRIDAY'S RESEARCH:\n{friday}\n"

        # 2) TRON — execution/build assessment
        tron = self._ask(TRON_SYS, ctx + "\nGive your execution assessment, TRON."); self._audit("TRON", tron)
        ctx += f"\nTRON'S EXECUTION VIEW:\n{tron}\n"

        # 3) ULTRON — critique
        ultron = self._ask(ULTRON_SYS, ctx + "\nAttack this, ULTRON — objections and the biggest flaw.")
        self._audit("ULTRON", ultron)
        ctx += f"\nULTRON'S OBJECTIONS:\n{ultron}\n"

        # 4) IRA — safety/risk (grounded by real SafetyGuard) + veto
        guard = self._ira_risk(task)
        ira = self._ask(IRA_SYS, ctx + f"\nSafetyGuard pre-check says: {guard}\nGive your risk verdict, IRA.")
        self._audit("IRA", ira)
        ctx += f"\nIRA'S SAFETY VERDICT:\n{ira}\n"
        approval_required = any(w in ira.upper() for w in ("CRITICAL", "HIGH"))

        # 5) MYTHOS — creativity/uniqueness upgrade
        mythos = self._ask(MYTHOS_SYS, ctx + "\nElevate this, MYTHOS — one or two high-leverage upgrades.")
        self._audit("MYTHOS", mythos)
        ctx += f"\nMYTHOS'S UPGRADES:\n{mythos}\n"

        # 6) JARVIS — synthesis & final decision
        jarvis = self._ask(JARVIS_SYS, ctx + (
            "\n\nApproval status: " + ("MASTER APPROVAL REQUIRED (IRA flagged elevated risk)."
            if approval_required else "within safe/auto bounds.") +
            "\nNow give your final decision for the master in this exact shape (spoken, no markdown):\n"
            "Final decision: ...\nWhy this is the best version: ...\nWhat was improved: ...\n"
            "What risks remain: ...\nWhat the master should do next: ..."))
        self._audit("JARVIS", jarvis)

        # learn from the council session
        try:
            if hasattr(self.orch, "experience"):
                self.orch.experience.record("council: " + task,
                    ["friday", "tron", "ultron", "ira", "mythos"], jarvis[:200])
        except Exception:
            pass
        if hasattr(self.orch, "live"):
            try: self.orch.live.done("council complete", True)
            except Exception: pass

        out = [
            f"AGENT COUNCIL REVIEW  ({started})",
            "=" * 52,
            "FRIDAY — research:\n" + (friday or "(no input)"),
            "\nTRON — implementation:\n" + (tron or "(no input)"),
            "\nULTRON — objections:\n" + (ultron or "(no input)"),
            "\nIRA — safety/risk:\n" + (ira or "(no input)"),
            "\nMYTHOS — improvement:\n" + (mythos or "(no input)"),
            "=" * 52,
            jarvis or "(JARVIS could not synthesise a decision)",
        ]
        if approval_required:
            out.append("\n⚠ IRA flagged elevated risk — I will NOT proceed without your explicit approval, sir.")
        return "\n".join(out)
