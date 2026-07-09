from __future__ import annotations
import os
from tools.base_tool import BaseTool

class BusinessTool(BaseTool):
    name = "business"; scope = "business_knowledge/"
    def __init__(self, context=None, logger=None):
        super().__init__(context, logger)
        self.dir = "business_knowledge"
    def read(self, filename: str) -> str:
        path = os.path.join(self.dir, filename)
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return f"[not found] {filename} — seed it in business_knowledge/."
    def files(self) -> list:
        try:
            return sorted(f for f in os.listdir(self.dir) if f.endswith(".md"))
        except OSError:
            return []
