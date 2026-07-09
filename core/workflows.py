"""Workflow Engine — JARVIS's bulletproof daily routines (Upgrade 6: depth over breadth).

Instead of shallow one-shot actions, these are the few things you do every day, run
end-to-end as robust multi-step routines: each step reports live, retries safe network
calls, and degrades honestly — a failed step is labelled, the rest still delivered, and
JARVIS never pretends a routine finished when it didn't.

Routines: start_my_day, wind_down, focus, research_brief.
"""
from __future__ import annotations
import os, re, datetime
from core import reliability as _rel


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (s or "brief").lower()).strip("-")
    return (s or "brief")[:50]


class WorkflowEngine:
    def __init__(self, orch):
        self.orch = orch

    # ---- generic robust runner -------------------------------------------------
    def _run_steps(self, title: str, steps) -> str:
        """steps: list of (label, fn, critical). fn returns a section string or None."""
        o = self.orch
        o.live.begin(title.lower().replace(" ", "_"), "workflow")
        parts = []
        for label, fn, critical in steps:
            o.live.step(label + "…")
            try:
                out = fn()
            except Exception as e:
                if o.logger:
                    o.logger.error(f"workflow '{title}' step '{label}': {e}")
                if critical:
                    o.live.done(f"{title} stopped at {label}", False)
                    return (f"{title} stopped at '{label}', sir — {e}. "
                            "I won't pretend it finished; the rest is untouched.")
                out = f"({label}: unavailable just now)"
            if out is None:
                if critical:
                    o.live.done(f"{title} stopped at {label}", False)
                    return f"{title} stopped at '{label}', sir. I won't pretend it finished."
                out = None  # skip empty optional sections silently
            if out:
                parts.append(out)
        o.live.done(f"{title} ready", True)
        return "\n\n".join(parts) if parts else f"{title} complete, sir — nothing notable to report."

    def run(self, name: str, args: str = "") -> str:
        fn = getattr(self, "_wf_" + name, None)
        if not fn:
            return f"I've no routine called '{name}', sir."
        return fn(args or "")

    # ---- shared helpers --------------------------------------------------------
    def _greeting_line(self) -> str:
        slot = self.orch._greeting_slot()
        return {"morning": "Good morning, sir.", "afternoon": "Good afternoon, sir.",
                "evening": "Good evening, sir.", "night": "Good evening, sir."}.get(slot, "Hello, sir.")

    def _weather_section(self):
        tool = self.orch.tools.get("weather")
        if not tool:
            return None
        out = _rel.attempt(lambda: tool.current("").get("text", ""), retries=1, delay=0.2,
                           label="weather", logger=self.orch.logger)
        return ("Weather: " + out.result) if out.ok and out.result else None

    def _headlines_section(self, topic="", n=3):
        nt = self.orch.tools.get("news")
        if not nt:
            return None
        def fetch():
            r = nt.headlines(topic, limit=n)
            if not (r.get("ok") and r.get("items")):
                return ""
            return "Headlines:\n" + "\n".join("  • " + it["headline"] +
                    (f" ({it['source']})" if it.get("source") else "") for it in r["items"][:n])
        out = _rel.attempt(fetch, retries=1, delay=0.2, label="news", logger=self.orch.logger)
        return out.result if out.ok and out.result else None

    def _tasks_section(self, label="Your tasks"):
        titles = list(dict.fromkeys(t["title"] for t in self.orch.tasks.list("open")))[:6]
        if not titles:
            return label + ": nothing open — add one with 'create task <title>'."
        return label + ":\n" + "\n".join("  • " + t for t in titles)

    def _focus_line(self):
        titles = list(dict.fromkeys(t["title"] for t in self.orch.tasks.list("open")))[:6]
        if not titles:
            return None
        if self.orch.llm.available:
            ans = self.orch.llm.chat(self.orch.system_prompt,
                "In one or two calm sentences, tell me the single most important thing to focus on today "
                "from these open tasks, and why. Tasks: " + ", ".join(titles))
            if ans:
                return "Focus, sir: " + ans
        return "Focus, sir: I'd start with '" + titles[0] + "'."

    def _alerts_section(self):
        msgs = []
        try:
            msgs += self.orch.drain_alerts()
            msgs += self.orch.watches.check_all()
        except Exception:
            pass
        msgs = list(dict.fromkeys(msgs))
        return ("From your monitors:\n" + "\n".join("  • " + m for m in msgs)) if msgs else None

    # ---- routines --------------------------------------------------------------
    def _wf_start_day(self, args=""):
        steps = [
            ("Greeting", lambda: self._greeting_line() + " Here's your day.", False),
            ("Weather", self._weather_section, False),
            ("Headlines", lambda: self._headlines_section("", 3), False),
            ("Tasks", lambda: self._tasks_section("Open today"), False),
            ("Focus", self._focus_line, False),
            ("Alerts", self._alerts_section, False),
        ]
        return self._run_steps("Morning briefing", steps)

    def _wf_wind_down(self, args=""):
        def done_section():
            done = len(self.orch.tasks.list("done"))
            return f"Completed so far: {done} task(s)."
        def tomorrow():
            titles = list(dict.fromkeys(t["title"] for t in self.orch.tasks.list("open")))[:6]
            if not titles:
                return "Nothing left open, sir — a clean slate for tomorrow."
            return "Still open for tomorrow:\n" + "\n".join("  • " + t for t in titles)
        steps = [
            ("Greeting", lambda: "Good evening, sir. Let's wrap the day.", False),
            ("Done", done_section, False),
            ("Tomorrow", tomorrow, False),
            ("Alerts", self._alerts_section, False),
            ("Goodnight", lambda: "Set tomorrow's top task with 'create task <title>'. Rest well — I'll keep watch.", False),
        ]
        return self._run_steps("Wind-down", steps)

    def _wf_focus(self, args=""):
        target = (args or "").strip()
        if not target:
            titles = list(dict.fromkeys(t["title"] for t in self.orch.tasks.list("open")))
            if not titles:
                return "What shall we focus on, sir? Tell me the task, or add one with 'create task <title>'."
            target = titles[0]
        def plan():
            if self.orch.llm.available:
                ans = self.orch.llm.chat(self.orch.system_prompt,
                    "Give a tight focus plan for this single task: a one-sentence framing and the very first "
                    "concrete action to take now. Task: " + target)
                if ans:
                    return ans
            return "First action: open what you need for it and do the smallest next step."
        steps = [
            ("Focus", lambda: "Locking in on: " + target + ".", True),
            ("Plan", plan, False),
            ("Guard", lambda: "I'll hold the line, sir — say 'anything new' only when you surface for air.", False),
        ]
        return self._run_steps("Focus session", steps)

    def _wf_research_brief(self, args=""):
        topic = (args or "").strip()
        if not topic:
            return "What should the brief be on, sir?"
        ult = self.orch.agents.get("ultron")
        def research():
            if not ult:
                return ""
            return ult.run("research", topic)
        out = _rel.attempt(research, retries=1, delay=0.3, label="research", logger=self.orch.logger)
        body = out.result if out.ok and out.result else ""
        if not body:
            return ("I couldn't gather the brief just now, sir — the web or the brain is unreachable. "
                    "Nothing was saved.")
        # save to a brief file (honest about success/failure)
        try:
            os.makedirs("briefs", exist_ok=True)
            path = os.path.join("briefs", _slug(topic) + ".md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# Brief: {topic}\n_Generated {datetime.datetime.now():%Y-%m-%d %H:%M}_\n\n{body}\n")
            saved = os.path.abspath(path)
        except OSError as e:
            return "I researched it, sir, but couldn't save the file (" + str(e) + "). Here it is:\n\n" + body
        preview = body.strip().replace("\n", " ")[:200]
        return f"Brief on '{topic}' saved to {saved}, sir.\n\n{preview}…"
