from __future__ import annotations
from tools.base_tool import BaseTool

NEG = {"angry", "terrible", "refund", "broken", "worst", "scam", "late", "never", "disappointed", "wrong"}

class CustomerSupportTool(BaseTool):
    """Drafts professional replies. Never sends."""
    name = "customer_support"; scope = "draft only"
    def detect_tone(self, msg: str) -> str:
        low = (msg or "").lower()
        hits = sum(1 for w in NEG if w in low)
        if hits >= 2: return "upset"
        if hits == 1: return "concerned"
        return "neutral"
    def draft_reply(self, msg: str) -> str:
        if not msg.strip():
            return "Paste the customer's message after the command and I'll draft a reply."
        tone = self.detect_tone(msg)
        opener = {
            "upset": "I'm really sorry for the trouble — that's not the experience we want for you.",
            "concerned": "Thanks for reaching out, and sorry for any hassle here.",
            "neutral": "Thanks so much for getting in touch!",
        }[tone]
        return (f"Detected tone: {tone}\n"
                "---\n"
                f"Hi [name],\n\n{opener}\n\n"
                "So I can fix this fast, could you share your order number and a photo if relevant? "
                "Once I have that, I'll [offer replacement/refund/solution] right away.\n\n"
                "Thanks for your patience — I'll make this right.\n\n"
                "Warm regards,\n[Your name]\n---")
