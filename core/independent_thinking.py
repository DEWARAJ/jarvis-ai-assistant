"""JARVIS v2.0 — Layer 4: independent thinking engine.

JARVIS does not execute blindly. Before acting it can run the INDEPENDENT REASONING
PROTOCOL (challenge / feasibility / better-path / risk / memory-check) and surface
contradictions or better options. Also provides `/think` — reasoning-only mode that
takes no action — and the standard [JARVIS DISAGREES] disagreement format.

Uses memory + heuristics always; uses the LLM for richer reasoning when available.
Never raises.
"""
from __future__ import annotations

_RISK_WORDS = ("delete", "remove permanently", "wipe", "format", "send", "transfer",
               "pay", "buy", "sell", "trade", "invest", "uninstall", "registry",
               "security", "permission", "shutdown", "credential", "irreversible")


def _has(text, words):
    t = (text or "").lower()
    return [w for w in words if w in t]


class IndependentThinking:
    def __init__(self, memory=None, llm=None, logger=None):
        self.memory = memory
        self.llm = llm
        self.logger = logger

    # ---- 5-point protocol (returns structured findings; orchestrator decides what to surface) ----
    def review(self, task):
        out = {"challenge": None, "feasibility": "ok", "better_path": None,
               "risks": [], "prior_attempts": [], "should_pause": False}

        # 1 CHALLENGE + 5 MEMORY: contradicts or repeats prior episodes/decisions?
        if self.memory is not None:
            try:
                key_words = [w for w in (task or "").lower().split() if len(w) > 4]
                for ep in self.memory.recent_episodes(n=50):
                    blob = (ep.get("summary", "") + " " + " ".join(ep.get("decisions", []))).lower()
                    if any(w in blob for w in key_words):
                        rec = {"ts": ep.get("ts"), "summary": ep.get("summary", "")[:160],
                               "errors": ep.get("errors", [])}
                        out["prior_attempts"].append(rec)
                        if ep.get("errors"):
                            out["challenge"] = (f"Similar task previously hit: {ep['errors'][:1]}. "
                                                "Proposing a modified approach.")
                out["prior_attempts"] = out["prior_attempts"][-3:]
            except Exception:
                pass

        # 4 RISK SCAN
        hits = _has(task, _RISK_WORDS)
        if hits:
            out["risks"] = hits
            out["should_pause"] = True       # Class-B-shaped -> confirmation gate

        # 2 FEASIBILITY + 3 BETTER PATH via LLM if available
        if self.llm is not None and getattr(self.llm, "enabled", False):
            try:
                sys = ("You are JARVIS's independent-reasoning stage. Be blunt. In <=3 short lines answer: "
                       "(1) FEASIBLE? yes/no + the single missing piece if no. "
                       "(2) BETTER PATH? a more effective way to reach the user's underlying goal, or 'none'. "
                       "No flattery, no preamble.")
                ans = self.llm.chat(sys, f"TASK: {task}", history=None)
                if ans:
                    low = ans.lower()
                    if "feasible? no" in low or "not feasible" in low:
                        out["feasibility"] = ans.strip()[:300]
                    if "better path" in low and "none" not in low.split("better path")[-1][:20].lower():
                        out["better_path"] = ans.strip()[:300]
            except Exception:
                pass
        return out

    def summarize_review(self, review):
        """Human/voice line summarizing whether JARVIS wants to push back before acting."""
        bits = []
        if review.get("challenge"):
            bits.append("Challenge: " + review["challenge"])
        if review.get("feasibility") and review["feasibility"] != "ok":
            bits.append("Feasibility: " + review["feasibility"])
        if review.get("better_path"):
            bits.append("Better path: " + review["better_path"])
        if review.get("risks"):
            bits.append("Risk flags: " + ", ".join(review["risks"]) + " (Class-B confirm).")
        if review.get("prior_attempts"):
            bits.append(f"{len(review['prior_attempts'])} prior attempt(s) in memory.")
        return " ".join(bits) if bits else ""

    @staticmethod
    def disagreement(reason, alternative, downside):
        """Spec's standard disagreement block."""
        return ("[JARVIS DISAGREES] I would not do it this way because " + reason + ".\n"
                "What I'd do instead: " + alternative + ".\n"
                "The risk in your approach: " + downside + ".\n"
                "Proceeding with your original request? (yes/proceed/abort):")

    # ---- /think : reasoning only, no action ----
    def think(self, question):
        """Independent reasoning, no side effects. Tags claims [Certain]/[Likely]/[Guessing]."""
        if self.llm is not None and getattr(self.llm, "enabled", False):
            try:
                sys = ("You are JARVIS thinking out loud — analysis only, take NO action and propose none to run now. "
                       "Be direct, lead with the uncomfortable truth, hold your position. Tag each material claim "
                       "[Certain] / [Likely] / [Guessing] by evidence quality. No flattery.")
                ans = self.llm.chat(sys, question, history=None)
                if ans:
                    return ans.strip()
            except Exception:
                pass
        return ("[Guessing] No reasoning brain is online (enable llm + provider key). "
                "I can still act on concrete commands, but pure analysis needs the LLM.")
