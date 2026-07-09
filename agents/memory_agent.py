from agents.base_agent import BaseAgent

class MemoryAgent(BaseAgent):
    role = "Stores safe local memory; prevents storing secrets."
    def run(self, action, args="", plan=None):
        mem = self.memory
        if action == "overview":
            ov = mem.overview() if mem else {}
            return self._header("Memory overview", plan) + "\n" + \
                "\n".join(f"  {k}: {v}" for k, v in ov.items())
        if action == "remember" and mem:
            cat, _, content = (args or "").partition(":")
            res = mem.remember(cat.strip(), content.strip())
            return res["msg"]
        return super().run(action, args, plan)
