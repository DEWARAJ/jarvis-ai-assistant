from __future__ import annotations
from tools.base_tool import BaseTool

CONNECTORS = ["gmail", "google_calendar", "google_drive", "shopify", "meta_ads",
              "instagram", "tiktok", "google_analytics", "stripe", "paypal",
              "notion", "slack", "discord", "telegram", "browser", "broker_paper"]

class PlaceholderConnectors(BaseTool):
    """All external connectors are DISABLED until explicitly approved by Master."""
    name = "connectors"; scope = "disabled until approved"
    def status(self) -> str:
        return "External connectors (all DISABLED in Phase 1):\n  " + ", ".join(CONNECTORS)
    def call(self, name: str, *a, **k) -> str:
        return f"[blocked] Connector '{name}' is disabled. External APIs require explicit Master approval."
