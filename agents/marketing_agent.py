from agents.base_agent import BaseAgent

class MarketingAgent(BaseAgent):
    role = "Ad strategy, hooks, UGC scripts, landing angles, email/SMS."
    def run(self, action, args="", plan=None):
        if action == "ad_hooks":
            product = args or "your product"
            thought = self.think(
                f"Write 5 punchy, scroll-stopping ad hooks for: {product}. "
                "Then give a 1-line test plan. Keep it tight.",
                context_note="No ad spend happens without the Master's approval.")
            if thought:
                return self._header("Ad hooks", plan) + "\n" + thought + \
                    "\n(No ad spend without approval.)"
            # fallback template
            hooks = [
                f"\"The {product} mistake costing you sales every day.\"",
                f"\"I tried {product} for 30 days — here's what changed.\"",
                f"\"Stop scrolling if you've ever struggled with [pain {product} solves].\"",
                f"\"Why {product} sells out (and what makes it different).\"",
                f"\"POV: you finally found a {product} that just works.\"",
            ]
            return self._header("Ad hooks", plan) + "\n" + \
                "\n".join(f"  {i+1}. {h}" for i, h in enumerate(hooks)) + \
                "\nTest plan: run 3 hooks x 1 creative, kill below-CTR losers after 48h. (No ad spend without approval.)"
        return super().run(action, args, plan)
