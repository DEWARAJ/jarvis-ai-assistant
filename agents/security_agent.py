from agents.base_agent import BaseAgent

class SecurityAgent(BaseAgent):
    role = "Checks keys, privacy, unsafe commands, dangerous automations."
    def run(self, action, args="", plan=None):
        if action in ("review", "check", "audit"):
            mem = self.memory
            secret = mem.looks_like_secret(args) if mem else False
            verdict = "BLOCK — contains a suspected secret." if secret else "No secret detected in input."
            return self._header("Security review", plan) + (
                f"\nInput check: {verdict}\n"
                "Standing rules: no stored passwords/keys, no external calls, "
                "destructive ops need a backup, risky actions need confirmation.")
        return super().run(action, args, plan)
