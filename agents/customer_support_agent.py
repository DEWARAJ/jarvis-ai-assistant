from agents.base_agent import BaseAgent

class CustomerSupportAgent(BaseAgent):
    role = "Drafts customer replies. NEVER sends without approval."
    risk = "medium"
    def run(self, action, args="", plan=None):
        if action == "draft_reply":
            tool = self.tool("customer_support")
            tone = tool.detect_tone(args) if tool else "neutral"
            thought = self.think(
                f"Draft a professional, warm customer-support reply to this message: \"{args}\". "
                "Apologize if needed, ask for order number, offer a concrete resolution. "
                "Do NOT invent order details.",
                context_note=f"Detected tone: {tone}. This is a draft only — it will not be sent automatically.")
            if thought:
                body = f"Detected tone: {tone}\n---\n{thought}\n---"
            else:
                body = tool.draft_reply(args) if tool else "(support tool unavailable)"
            return self._header("Customer reply DRAFT (not sent)", plan) + "\n" + body + \
                "\n\n[!] This is a draft only. JARVIS will not send anything without your explicit approval."
        return super().run(action, args, plan)
