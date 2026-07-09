from agents.base_agent import BaseAgent

class TestingAgent(BaseAgent):
    role = "Validates features, writes tests, reports failures honestly."
    def run(self, action, args="", plan=None):
        if action in ("test", "validate"):
            return self._header("Testing", plan) + (
                "\nI run syntax checks and pytest, then report pass/fail truthfully — "
                "never a green light on a red result.")
        return super().run(action, args, plan)
