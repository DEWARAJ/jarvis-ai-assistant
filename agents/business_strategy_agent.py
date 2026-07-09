from agents.base_agent import BaseAgent

class BusinessStrategyAgent(BaseAgent):
    role = "Growth, offers, pricing, positioning, funnel, brand."
    def run(self, action, args="", plan=None):
        if action == "business_review":
            biz = self.tool("business")
            profile = biz.read("business_profile.md") if biz else ""
            thought = self.think(
                "Give a sharp business review: assess positioning, offer/pricing, funnel, "
                "and competitive advantage, then list 3 prioritized actions. Be specific.",
                context_note=f"Business profile file:\n{profile[:2000]}")
            if thought:
                return self._header("Business review", plan) + "\n" + thought
            have = "loaded" if profile and "not found" not in profile.lower() else "empty (seed business_knowledge/)"
            return self._header("Business review", plan) + (
                f"\nBusiness profile: {have}\n"
                "Assessment lenses:\n"
                "  - Positioning: who exactly, what promise, why you.\n"
                "  - Offer/pricing: is there a clear hero offer + upsell path?\n"
                "  - Funnel: traffic -> page -> checkout -> retention leaks.\n"
                "  - Advantage: what compounds (brand, data, ops)?\n"
                "Prioritized actions: tighten ONE offer, fix the biggest funnel leak, "
                "add one trust lever. Want these as tasks?")
        return super().run(action, args, plan)
