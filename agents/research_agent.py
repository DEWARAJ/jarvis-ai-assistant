from agents.base_agent import BaseAgent

class ResearchAgent(BaseAgent):
    role = "Competitor/product/market research with source-backed summaries."
    def run(self, action, args="", plan=None):
        if action in ("research", "competitor", "market"):
            topic = args or "(unspecified)"
            return self._header("Research framing", plan) + (
                f"\nTopic: {topic}\n"
                "Web research is disabled in Phase 1 (no external calls without approval).\n"
                "Structured approach I'd take: define question -> gather sources -> "
                "compare claims -> summarize with citations -> flag uncertainty.")
        return super().run(action, args, plan)
