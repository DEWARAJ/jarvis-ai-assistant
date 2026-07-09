from agents.base_agent import BaseAgent

class EcommerceAgent(BaseAgent):
    role = "Store, product pages, conversion, trust, upsells, journey."
    def run(self, action, args="", plan=None):
        if action == "improve_product_page":
            thought = self.think(
                f"Audit this product page and list concrete conversion improvements: {args or '(no detail given)'}. "
                "Cover hero clarity, benefits, trust signals, imagery, social proof, offer clarity, "
                "CTA, risk reversal, and mobile speed. End with the top 3 quick wins.")
            if thought:
                return self._header("Product page improvement", plan) + "\n" + thought
            tool = self.tool("ecommerce")
            audit = tool.audit_product_page(args) if tool else ""
            return self._header("Product page improvement", plan) + "\n" + audit
        return super().run(action, args, plan)
