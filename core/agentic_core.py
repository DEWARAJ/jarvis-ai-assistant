"""Agentic Core — JARVIS's LLM tool-calling brain.

The reasoning core (rule-based) handles fast, exact commands. Everything else flows here:
the LLM reads what the master actually means, decides which real actions to take, and the
orchestrator executes them through its normal dispatch — so the SafetyGuard and the 3-tier
permission framework still gate anything risky. The model NEVER executes anything itself;
it only proposes a plan as JSON, which we validate and run.
"""
from __future__ import annotations
import json, re

# (action, needs_arg, description) — every action maps to a real, dispatch-handled intent.
CATALOG = [
    ("open_app", True, "Open an app, folder or website. arg: name e.g. chrome, notepad, downloads, instagram.com"),
    ("open_site", True, "Open a specific website/URL. arg: the url"),
    ("browser_google", True, "Search Google. arg: the query"),
    ("browser_youtube", True, "Open YouTube search results. arg: the query"),
    ("youtube_play", True, "Play something on YouTube right away. arg: what to play"),
    ("hermes_run", True, "Delegate a complex multi-step agentic task to the Hermes Agent and report its result. arg: the task/question"),
    ("hermes_code", True, "Hand a coding or automation build to the Hermes Agent (web+terminal+files). arg: what to build/fix"),
    ("browser_back", False, "Go back to the previous page."),
    ("scroll_down", False, "Scroll the page down."),
    ("scroll_up", False, "Scroll the page up."),
    ("close_tab", False, "Close the current browser tab."),
    ("close_app", True, "Close an application. arg: app name"),
    ("volume_up", False, "Turn the volume up."),
    ("volume_down", False, "Turn the volume down."),
    ("volume_mute", False, "Mute the volume."),
    ("volume_unmute", False, "Unmute the volume."),
    ("volume_set", True, "Set volume to a percent. arg: a number 0-100"),
    ("screenshot", False, "Take a screenshot."),
    ("see_screen", True, "Look at the screen and answer about it. arg: the question"),
    ("verify_screen", True, "Look at the screen and confirm whether something is true (act->look->verify). arg: what to verify, e.g. 'the video is playing'"),
    ("click_vision", True, "Click an element on screen by LOOKING for it (vision-grounded). arg: what to click, e.g. 'the Submit button'"),
    ("news", True, "Latest news. arg: a topic (ai, business, crypto, world, tech) or empty for top"),
    ("weather", True, "Current weather. arg: a city, or empty for local"),
    ("traffic", True, "Live traffic to a place. arg: the destination"),
    ("price", True, "Live price of a stock or crypto. arg: the symbol or name"),
    ("research", True, "Deep, source-backed web research via ULTRON. arg: the topic"),
    ("advise", True, "Get expert, web-referenced advice on a task via ULTRON. arg: the goal/task"),
    ("improve", True, "Get improvement ideas for something via ULTRON. arg: what to improve"),
    ("check_email", False, "Read a summary of recent email (read-only)."),
    ("create_task", True, "Add a task to the list. arg: the task title"),
    ("show_tasks", False, "List open tasks."),
    ("complete_task", True, "Mark a task done. arg: the task id number"),
    ("memory_remember", True, "Permanently remember a fact/preference about the master. arg: the fact"),
    ("daily_briefing", False, "Full briefing: news + tasks + focus."),
    ("wf_start_day", False, "Run the full morning routine: greeting, weather, headlines, tasks, focus, alerts."),
    ("wf_research_brief", True, "Research a topic deeply and save a brief file. arg: the topic"),
    ("situation", False, "Quick situational report."),
    ("wifi", True, "Wi-Fi control. arg: on, off, or empty to open settings"),
    ("bluetooth", True, "Bluetooth control. arg: on, off, or empty to open settings"),
    ("write_code", True, "Write and save code to a file. arg: a description of what to build"),
    ("run_command", True, "Run a terminal command (will ask you to confirm first). arg: the command"),
    ("delete_files", True, "Delete files (will ask you to confirm first). arg: pattern/path"),
    ("power_sleep", False, "Put the computer to sleep."),
    ("power_lock", False, "Lock the screen."),
    ("system_info", False, "Report CPU, memory, disk, battery."),
    # ---- trading bot (Class A: read-only / simulation) ----
    ("bot_signals", False, "Run a live trading signal scan. No orders placed."),
    ("bot_backtest", True, "Run a historical backtest. arg: number of days, e.g. 30"),
    ("bot_walkforward", True, "Run walk-forward out-of-sample validation. arg: number of days, e.g. 45"),
    ("bot_pnl", False, "Show trading bot P&L and win-rate from the trade log."),
    ("bot_paper_status", False, "Check whether paper trading is currently running."),
    ("bot_paper_stop", False, "Stop the background paper-trading process."),
    # ---- utility tools ----
    ("utility_convert", True, "Convert units. arg: e.g. '100 celsius to fahrenheit' or '5 km to miles'"),
    ("utility_bmi", True, "Calculate BMI. arg: e.g. 'weight 70 height 175 cm'"),
    ("utility_calc", True, "Evaluate arithmetic safely. arg: the expression, e.g. '15% of 200'"),
    ("utility_joke", False, "Tell a joke."),
    ("utility_translate", True, "Translate text via the LLM brain. arg: e.g. 'hello world to spanish'"),
    ("utility_password", True, "Generate a secure password. arg: optional length or 'memorable'"),
    ("utility_calories", True, "Estimate daily calorie needs. arg: age weight height sex activity level"),
    # ---- browser tab management ----
    ("list_tabs", False, "List all open Chrome tabs by title and URL."),
]

_VALID = {a for a, _n, _d in CATALOG}
MAX_STEPS = 8  # raised from 4; ceiling hit is now logged, not silent


class AgenticCore:
    def __init__(self, orch):
        self.orch = orch

    # ---- prompt building ----
    def _catalog_text(self) -> str:
        lines = []
        for a, needs, desc in CATALOG:
            tag = " (needs arg)" if needs else " (no arg)"
            lines.append(f"- {a}{tag}: {desc}")
        return "\n".join(lines)

    def _system(self) -> str:
        return (
            "You are JARVIS's action planner - the part of the brain that turns the master's natural words "
            "into real actions on his Windows computer. You understand intent, not just keywords.\n\n"
            "Reply with ONLY a single JSON object, no prose, no code fences:\n"
            '{"say": "<see rules below for what goes here>", '
            '"steps": [{"action": "<exact action name>", "arg": "<string, empty if none>"}]}\n\n'
            "RULES — read all before responding:\n\n"
            "1. DEVICE/WEB/FILE ACTIONS (opening apps, searching, clicking, controlling media, etc.):\n"
            "   - List the steps in order. You may chain up to 8 steps.\n"
            "   - Put ONE short spoken British-butler sentence in say (e.g. 'Right away, sir.').\n"
            "   - The action results are appended automatically — do not narrate them in say.\n\n"
            "2. SUBSTANTIVE TASKS — research, brainstorm, analyze, propose, plan, explain, build, compare,\n"
            "   summarize, write, generate, give ideas, give options, strategy, report, brief:\n"
            "   - steps: []\n"
            "   - Put the COMPLETE FINISHED RESULT in say. Not a teaser. Not 'I have several ideas lined up'.\n"
            "   - Deliver the actual content in full. If asked for app ideas, write the ideas. If asked to\n"
            "     research, write the findings. Do not announce what you are about to do — do it.\n"
            "   - Length as needed: a short question gets a short answer; a research request gets full depth.\n\n"
            "3. CASUAL CHAT / SIMPLE QUESTION:\n"
            "   - steps: []\n"
            "   - Full answer in say, natural British-butler tone, as long as the answer needs to be.\n\n"
            "4. NEVER invent an action name. Only use names from the AVAILABLE ACTIONS list.\n"
            "   If no action fits a task, put steps: [] and answer fully in say.\n"
            "5. Risky actions (run_command, delete_files, power_*) are allowed — the system will gate them.\n\n"
            "AVAILABLE ACTIONS:\n" + self._catalog_text()
        )

    def _context(self) -> str:
        try:
            open_n = self.orch.tasks.open_count()
        except Exception:
            open_n = 0
        return f"Context: brain={self.orch.llm.active}, open_tasks={open_n}."

    # ---- json parsing ----
    @staticmethod
    def _extract_json(text: str):
        text = (text or "").strip()
        if not text:
            return None
        # strip code fences if present
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.find("{"):] if "{" in text else text
        try:
            return json.loads(text)
        except Exception:
            pass
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

    def _ask_plan(self, raw: str, history):
        out = self.orch.llm.chat(self._system(),
                                 "Master's request: " + raw + "\n\n" + self._context() +
                                 "\n\nRespond with ONLY the JSON object.",
                                 history=history)
        if not out:
            return None
        data = self._extract_json(out)
        if data is None:
            # model answered in prose - treat as a spoken reply
            return {"say": out.strip(), "steps": []}
        if not isinstance(data, dict):
            return {"say": str(out).strip(), "steps": []}
        return data

    # ---- main entry ----
    def plan_and_run(self, raw: str, history=None):
        """Return a spoken reply, or None to let the caller fall back."""
        llm = self.orch.llm
        if not (llm and getattr(llm, "available", False)):
            return None
        plan = self._ask_plan(raw, history)
        if plan is None:
            return None
        say = (plan.get("say") or "").strip()
        steps = plan.get("steps") or []
        if not isinstance(steps, list):
            steps = []
        # pure conversation / answer
        if not steps:
            return say or None
        parts = []
        # Only prepend say when it's a short butler preamble ("Right away, sir.").
        # If say already contains a full answer AND steps also produce output, both
        # get concatenated → the double-answer bug. Suppress say when it looks like
        # a complete response (>120 chars) so action results speak for themselves.
        if say and len(say) <= 120:
            parts.append(say)
        self.orch.live.begin("agentic", "tool-calling")
        ran = 0
        for st in steps[:MAX_STEPS]:
            if not isinstance(st, dict):
                continue
            action = (st.get("action") or "").strip()
            arg = str(st.get("arg") or "").strip()
            if action not in _VALID:
                continue
            ran += 1
            self.orch.live.step((f"{action} {arg}").strip())
            try:
                res = self.orch._run_action(action, arg)
            except Exception as e:
                res = f"(I hit a snag on '{action}', sir: {e})"
            if res:
                parts.append(res)
            # Phase 2 completion loop: run the Class A chain to completion, but the moment a
            # step raises a Class B confirmation (sets orch.pending), pause the rest here
            # rather than blindly executing past a gate.
            if getattr(self.orch, "pending", None):
                parts.append("I'll hold the rest here, sir — the step above needs your confirmation first.")
                break
        if len(steps) > MAX_STEPS:
            over = len(steps) - MAX_STEPS
            if self.orch.logger:
                self.orch.logger.warn(f"[agentic] step ceiling hit: plan had {len(steps)} steps, ran {MAX_STEPS}, dropped {over}")
        self.orch.live.done("done", True)
        if ran == 0:
            return say or None
        return "\n".join(p for p in parts if p).strip() or (say or "Done, sir.")

    # ---- true ReAct agent loop (observe -> think -> act -> observe -> self-correct) ----
    def _loop_system(self) -> str:
        lines = [
            "You are JARVIS operating as an autonomous agent on a Windows computer. Pursue the goal ONE "
            "step at a time, like a careful human operator: see what happened, then choose the single best "
            "next action. You have eyes (see_screen, verify_screen) and can click what you see (click_vision).",
            "",
            "Each turn reply with ONLY one JSON object:",
            '  {"thought":"one short line","action":"<exact action name>","arg":"<string>"}  to act, OR',
            '  {"done":true,"summary":"<what you achieved, or why you are blocked>"}  when finished/stuck.',
            "",
            "Rules: exactly one action per turn; use ONLY the listed action names; verify important results "
            "with see_screen/verify_screen before declaring done; if the same step fails twice, stop and "
            "report honestly (done=true with the reason). Risky actions (delete, power, run_command) will "
            "ask the master to confirm first - that is expected.",
            "",
            "ACTIONS:",
        ]
        return "\n".join(lines) + "\n" + self._catalog_text()

    def act_loop(self, goal: str, max_steps: int = 6):
        """Run an iterative agent loop. Returns the final spoken result, or None to fall back."""
        llm = self.orch.llm
        if not (llm and getattr(llm, "available", False)):
            return None
        goal = (goal or "").strip()
        if not goal:
            return "Give me a goal, sir, and I'll work it step by step."
        transcript = []
        self.orch.live.begin("agent", "react-loop")
        sysp = self._loop_system()
        for i in range(max_steps):
            obs = "\n".join(transcript) if transcript else "(nothing done yet)"
            out = llm.chat(sysp, "Goal: " + goal + "\n\nProgress so far:\n" + obs +
                           "\n\nYour next step as JSON only.")
            data = self._extract_json(out)
            if not isinstance(data, dict):
                self.orch.live.done("agent: replied", True)
                return out or None
            if data.get("done"):
                self.orch.live.done("agent: done", True)
                summ = data.get("summary") or "Done, sir."
                if transcript:
                    return summ + "\n\nSteps taken:\n" + "\n".join("  " + t for t in transcript)
                return summ
            action = (data.get("action") or "").strip()
            arg = str(data.get("arg") or "").strip()
            if action not in _VALID:
                transcript.append(f"{i+1}. (skipped invalid action '{action}')")
                continue
            self.orch.live.step((f"{i+1}: {action} {arg}").strip())
            try:
                res = self.orch._run_action(action, arg)
            except Exception as e:
                res = f"(error: {e})"
            transcript.append(f"{i+1}. {action} {arg} -> " + " ".join(str(res).split())[:160])
        self.orch.live.done("agent: step limit", True)
        return "I reached my step limit, sir. Here's what I did:\n" + "\n".join("  " + t for t in transcript)
