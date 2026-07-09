from __future__ import annotations
from tools.base_tool import BaseTool

CHECKS = [
    ("Hero clarity", "Does the first screen state what it is + who it's for in 5 seconds?"),
    ("Primary benefit", "Lead benefit above the fold, not just features."),
    ("Trust signals", "Reviews, ratings, guarantees, secure-checkout badges visible."),
    ("Imagery", "Multiple angles + lifestyle/UGC shots."),
    ("Social proof", "Real review count + star average near the buy button."),
    ("Offer clarity", "Price, shipping, returns, and any bundle/upsell are obvious."),
    ("CTA", "One dominant 'Add to cart' button, repeated on long pages."),
    ("Risk reversal", "Money-back/returns clearly stated to lower purchase anxiety."),
    ("Speed/mobile", "Fast load + clean mobile layout (most traffic is mobile)."),
]

class EcommerceTool(BaseTool):
    name = "ecommerce"; scope = "audit & copy"
    def audit_product_page(self, notes: str) -> str:
        ctx = f"Target: {notes}\n" if notes.strip() else ""
        body = "\n".join(f"  [{i+1}] {name}: {q}" for i, (name, q) in enumerate(CHECKS))
        return (ctx + "Product-page audit checklist (score each 0–2, aim for 16+):\n" + body +
                "\nQuick wins usually: add reviews near CTA, stronger hero promise, "
                "clear returns policy, faster mobile images.")
