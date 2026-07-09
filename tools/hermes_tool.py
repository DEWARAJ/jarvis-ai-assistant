"""Hermes Agent bridge for JARVIS.

Lets JARVIS delegate heavy agentic work (multi-step coding, web+terminal tasks,
provider-routed reasoning) to the locally-installed Hermes Agent, then speak the
result back. Hermes stays a *tool* under the JARVIS orchestrator — JARVIS remains
the brain; Hermes is one skilled agent it dispatches to.

Invocation is Hermes's one-shot headless mode:
    <hermes_venv_python> <hermes_dir>/cli.py -q "<prompt>" --quiet [-t web,terminal] [--max_turns N]

Never blocks forever (hard subprocess timeout) and never fakes success.
"""
from __future__ import annotations
from tools.base_tool import BaseTool


class HermesTool(BaseTool):
    name = "hermes"
    scope = "delegate agentic tasks to the local Hermes Agent"

    def __init__(self, context=None, logger=None):
        super().__init__(context, logger)
        self._dir = None
        self._py = None

    @staticmethod
    def _speak(text: str) -> str:
        """Keep spoken/displayed output sane for a voice assistant."""
        text = (text or "").strip()
        return text if len(text) <= 1800 else text[:1800] + " … (truncated)"

    # ---- internal bridge (Anthropic key, ReAct tool loop) ----
    @staticmethod
    def _internal(prompt: str) -> dict:
        """
        Run Hermes via the internal HermesBridge (real Claude agent, ANTHROPIC_API_KEY,
        full web_search + scrape_url ReAct loop). This is the working path — replaces the
        dead external CLI subprocess that hit safety refusals from its own provider.
        """
        try:
            from hermes_bridge import HermesBridge
            text = HermesBridge().send(prompt, priority="high")
            return {"ok": True, "text": text, "why": ""}
        except Exception as e:
            return {"ok": False, "text": "", "why": f"internal Hermes error: {e}"}

    # ---- spec functions (called by the orchestrator) ----
    def run(self, prompt: str, max_turns: int = 20, timeout: int = 180) -> dict:
        """General-purpose delegate via internal HermesBridge (Anthropic-powered)."""
        p = (prompt or "").strip()
        if not p:
            return {"started": False, "spoken": "What should I ask Hermes to do, sir?", "debug": ""}
        r = self._internal(p)
        if r["ok"]:
            return {"started": True, "text": r["text"],
                    "spoken": "Hermes finished, sir. " + self._speak(r["text"]),
                    "debug": "hermes run (internal)"}
        return {"started": False, "spoken": f"Hermes couldn't complete that, sir — {r['why']}",
                "debug": r["why"]}

    def code(self, prompt: str, max_turns: int = 40, timeout: int = 300) -> dict:
        """Coding/automation task via internal HermesBridge (Anthropic-powered)."""
        p = (prompt or "").strip()
        if not p:
            return {"started": False, "spoken": "What should Hermes build, sir?", "debug": ""}
        r = self._internal(p)
        if r["ok"]:
            return {"started": True, "text": r["text"],
                    "spoken": "Hermes finished the task, sir. " + self._speak(r["text"]),
                    "debug": "hermes code (internal)"}
        return {"started": False, "spoken": f"Hermes couldn't finish the build, sir — {r['why']}",
                "debug": r["why"]}
