from agents.base_agent import BaseAgent

class ExecutiveAgent(BaseAgent):
    role = "Converts goals into strategy, priorities, and task order."
    def run(self, action, args="", plan=None):
        if action in ("prioritize", "business_review", "strategy"):
            goal = args or "current operations"
            return self._header("Executive priorities", plan) + (
                f"\nGoal: {goal}\n"
                "Top priorities (impact x effort):\n"
                "  1. Protect cash & margins (no risky spend).\n"
                "  2. Highest-leverage revenue lever this week.\n"
                "  3. Remove the single biggest bottleneck.\n"
                "Next: turn each into a task with 'create task <...>'.")
        return super().run(action, args, plan)
