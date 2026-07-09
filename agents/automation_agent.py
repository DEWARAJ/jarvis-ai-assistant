from agents.base_agent import BaseAgent

class AutomationAgent(BaseAgent):
    role = "Designs safe workflows & scripts. NEVER runs risky automation without approval."
    risk = "high"
    def run(self, action, args="", plan=None):
        if action in ("plan", "design", "workflow"):
            tool = self.tool("automation")
            return self._header("Automation plan (design only)", plan) + "\n" + \
                (tool.plan(args) if tool else "(automation tool unavailable)")
        return super().run(action, args, plan)
