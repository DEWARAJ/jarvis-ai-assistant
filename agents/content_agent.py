from agents.base_agent import BaseAgent

class ContentAgent(BaseAgent):
    role = "Captions, product descriptions, scripts, emails, copy."
    def run(self, action, args="", plan=None):
        if action in ("write", "caption", "description"):
            topic = args or "your product"
            return self._header("Content draft", plan) + (
                f"\nTopic: {topic}\n"
                "Hook: lead with the customer's pain or desire.\n"
                "Body: one clear benefit + proof.\n"
                "CTA: a single, specific next step.")
        return super().run(action, args, plan)
