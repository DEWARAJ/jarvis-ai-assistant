"""JARVIS v2.0 — Layer 2: OODA loop engine (Observe · Orient · Decide · Act).

Runs an explicit decision loop over a task and returns a structured trace plus a
spoken/printed narration ([OBS]/[ORI]/[DEC]/[ACT]). It does NOT execute side effects
itself — execution stays with the orchestrator's existing safety/permission-gated
dispatch. OODA produces: observations (incl. memory recall of similar past work),
candidate approaches with tradeoffs, a chosen approach, and flags
(needs_code_mod / needs_web / class_b) so the orchestrator routes correctly.

Works with or without an LLM. If a LLMClient is provided and enabled, Orient/Decide
get richer reasoning; otherwise heuristics are used. Never raises.
"""
from __future__ import annotations

# Keyword signals (cheap, overridable). Mirror the Class-A/B model in the persona.
_CLASS_B = (
    "delete", "remove", "send", "email", "message", "post", "publish", "tweet",
    "buy", "sell", "trade", "transfer", "pay", "purchase", "order", "invest",
    "install", "uninstall", "format", "shutdown", "restart", "registry",
    "permission", "security setting", "system setting", "credential", "password",
)
_CODE_MOD = ("modify your", "change your code", "self-modify", "adapt", "rewrite your",
             "add a capability", "new capability", "improve yourself", "edit the file",
             "fix the bug in", "refactor")
_WEB = ("search", "look up", "latest", "news", "price", "weather", "current", "online",
        "website", "browse", "google", "youtube", "fetch", "download")


def _flag(text, words):
    t = (text or "").lower()
    return any(w in t for w in words)


class OODALoop:
    def __init__(self, memory=None, llm=None, logger=None):
        self.memory = memory          # JarvisMemory (optional)
        self.llm = llm                # LLMClient (optional)
        self.logger = logger

    # ---- phases ----
    def observe(self, task):
        obs = {"task": task, "similar_past": [], "ambiguous": False, "notes": []}
        # Memory recall: have we done / failed something similar?
        if self.memory is not None:
            try:
                key = (task or "").lower()
                for ep in self.memory.recent_episodes(n=50):
                    blob = (ep.get("summary", "") + " " + " ".join(ep.get("tasks_completed", []))).lower()
                    if any(w in blob for w in key.split() if len(w) > 4):
                        obs["similar_past"].append({"ts": ep.get("ts"), "summary": ep.get("summary", "")[:160],
                                                     "errors": ep.get("errors", [])})
                obs["similar_past"] = obs["similar_past"][-3:]
            except Exception:
                pass
        if len((task or "").split()) < 2:
            obs["ambiguous"] = True
            obs["notes"].append("Task is very short — may need one clarifying question.")
        if obs["similar_past"]:
            obs["notes"].append(f"{len(obs['similar_past'])} similar past episode(s) found in memory.")
        return obs

    def orient(self, task, obs):
        ori = {"approaches": [], "assumptions": [], "risks": []}
        # Heuristic risks/assumptions
        if _flag(task, _CLASS_B):
            ori["risks"].append("Carries a Class-B action (financial/deletion/send/system) — needs confirmation.")
        if _flag(task, _CODE_MOD):
            ori["risks"].append("Requires self-modification — backup + approval + rollback path required.")
        for ep in obs.get("similar_past", []):
            if ep.get("errors"):
                ori["risks"].append(f"Past attempt logged errors: {ep['errors'][:1]}")
        # Approaches: ask the LLM for 2-3 with tradeoffs if available, else generic
        if self.llm is not None and getattr(self.llm, "enabled", False):
            try:
                sys = ("You are JARVIS's OODA Orient stage. Given a task, output 2-3 concrete approaches, "
                       "each ONE line as 'Approach: <name> — Tradeoff: <cost/risk>'. No preamble.")
                out = self.llm.chat(sys, f"TASK: {task}", history=None)
                if out:
                    for line in out.splitlines():
                        line = line.strip("-• ").strip()
                        if line and ("approach" in line.lower() or "—" in line or "-" in line):
                            ori["approaches"].append(line[:200])
                    ori["approaches"] = ori["approaches"][:3]
            except Exception:
                pass
        if not ori["approaches"]:
            ori["approaches"] = ["Approach: direct execution via existing tools — Tradeoff: fastest, no new code.",
                                 "Approach: adapt/extend a tool first — Tradeoff: slower, adds capability."]
        ori["assumptions"].append("Assuming current tools/permissions unless task states otherwise.")
        return ori

    def decide(self, task, obs, ori):
        dec = {
            "chosen": ori["approaches"][0] if ori["approaches"] else "direct execution",
            "needs_code_mod": _flag(task, _CODE_MOD),
            "needs_web": _flag(task, _WEB),
            "class_b": _flag(task, _CLASS_B),
            "rationale": "",
        }
        if dec["class_b"]:
            dec["rationale"] = "Chosen path includes a Class-B step — will dry-run and request confirmation."
        elif dec["needs_code_mod"]:
            dec["rationale"] = "Capability gap — routing to the self-adaptation pipeline (backup + approval)."
        elif obs.get("ambiguous"):
            dec["rationale"] = "Task underspecified — one clarifying question before acting."
        else:
            dec["rationale"] = "Class-A path — execute directly through normal dispatch."
        return dec

    def run(self, task, execute=None):
        """Run O-O-D. If `execute` callable is passed and the decision is Class-A & unambiguous,
        it is invoked with the task and its result captured in the ACT phase. Returns a trace dict."""
        obs = self.observe(task)
        ori = self.orient(task, obs)
        dec = self.decide(task, obs, ori)
        act = {"executed": False, "result": None, "deferred_reason": ""}
        if execute and not dec["class_b"] and not dec["needs_code_mod"] and not obs["ambiguous"]:
            try:
                act["result"] = execute(task)
                act["executed"] = True
            except Exception as e:
                act["result"] = f"execution error: {e}"
        else:
            act["deferred_reason"] = dec["rationale"]
        trace = {"observe": obs, "orient": ori, "decide": dec, "act": act}
        # Log intent to episodic memory (not a full session episode — a decision marker)
        if self.memory is not None:
            try:
                self.memory.append_episode(
                    summary=f"OODA on: {task}", decisions=[dec["chosen"]],
                    tasks_completed=(["executed"] if act["executed"] else []),
                    errors=([] if act["executed"] or not execute else ["deferred"]),
                    mood="deliberate")
            except Exception:
                pass
        return trace

    def narrate(self, trace):
        """Render the trace as the spec's tagged narration."""
        o, r, d, a = trace["observe"], trace["orient"], trace["decide"], trace["act"]
        lines = []
        lines.append(f"[OBS] Task: {o['task']}")
        if o["similar_past"]:
            lines.append(f"[OBS] Memory: {len(o['similar_past'])} similar past episode(s).")
        for n in o["notes"]:
            lines.append(f"[OBS] {n}")
        for ap in r["approaches"]:
            lines.append(f"[ORI] {ap}")
        for rk in r["risks"]:
            lines.append(f"[ORI] Risk: {rk}")
        lines.append(f"[DEC] Chosen: {d['chosen']}")
        flags = []
        if d["class_b"]: flags.append("CLASS-B confirm")
        if d["needs_code_mod"]: flags.append("self-adapt")
        if d["needs_web"]: flags.append("web")
        if flags:
            lines.append(f"[DEC] Flags: {', '.join(flags)}")
        lines.append(f"[DEC] {d['rationale']}")
        if a["executed"]:
            lines.append(f"[ACT] Executed. Result: {str(a['result'])[:300]}")
        else:
            lines.append(f"[ACT] Deferred — {a['deferred_reason']}")
        return "\n".join(lines)
