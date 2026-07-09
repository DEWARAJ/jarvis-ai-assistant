"""Base class for all tools. Tools are scoped and safe-by-default."""
from __future__ import annotations

class BaseTool:
    name = "base"
    scope = "none"
    def __init__(self, context: dict | None = None, logger=None):
        self.context = context or {}
        self.logger = logger
