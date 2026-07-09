from agents.base_agent import BaseAgent

class PersonalCompanionAgent(BaseAgent):
    role = "Daily planning, focus, routines, evening review."
    def _open_titles(self):
        tasks = self.tasks
        items = tasks.list("open") if tasks else []
        return [t["title"] for t in items]

    def run(self, action, args="", plan=None):
        tasks = self.tasks
        open_n = tasks.open_count() if tasks else 0
        titles = self._open_titles()
        if action == "daily_briefing":
            thought = self.think(
                "Give a short, motivating daily briefing and name the single most important focus.",
                context_note=f"Open tasks ({open_n}): {titles or 'none'}")
            if thought:
                return thought
            return ("Focus for today: protect deep-work time, ship one meaningful thing.\n"
                    f"You have {open_n} open task(s). Say 'plan my day' to sequence them.")
        if action == "plan_day":
            thought = self.think(
                "Plan my day: sequence these tasks by priority into morning/midday/afternoon "
                "time blocks with a one-line reason each.",
                context_note=f"Open tasks: {titles or 'none'}")
            if thought:
                return self._header("Plan my day", plan) + "\n" + thought
            if not titles:
                return self._header("Plan my day", plan) + \
                    "\nNo open tasks. Add 2-3 with 'create task <title>' and I'll block your day."
            lines = "\n".join(f"  - {t}" for t in titles[:6])
            return self._header("Plan my day", plan) + (
                "\nSuggested blocks:\n"
                "  Morning (deep work): hardest/most valuable task\n"
                "  Midday (ops): customer support, business review\n"
                "  Afternoon (lighter): content, research\n"
                f"Your open tasks:\n{lines}")
        if action == "evening_review":
            done = len(tasks.list("done")) if tasks else 0
            thought = self.think(
                "Run a brief, encouraging evening review and prompt me to set tomorrow's top task.",
                context_note=f"Done total: {done}. Still open: {open_n} -> {titles or 'none'}")
            if thought:
                return thought
            return ("Evening review:\n"
                    f"  Completed (total done): {done}\n"
                    f"  Still open: {open_n}\n"
                    "  Wins? Carry-overs? Set tomorrow's top 1 task now.")
        return super().run(action, args, plan)
