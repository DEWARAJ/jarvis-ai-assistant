from agents.base_agent import BaseAgent

class CodingAgent(BaseAgent):
    role = "Writes/refactors code, fixes bugs, adds tests — inside the project folder."
    risk = "medium"
    def run(self, action, args="", plan=None):
        if action in ("code", "refactor", "fix"):
            return self._header("Coding task", plan) + (
                f"\nRequest: {args or '(none)'}\n"
                "I write code only inside the project folder. Overwrites require confirmation.")
        return super().run(action, args, plan)
