from __future__ import annotations
import os
from datetime import datetime
from tools.base_tool import BaseTool

class NotesTool(BaseTool):
    name = "notes"; scope = "notes/"
    def __init__(self, context=None, logger=None):
        super().__init__(context, logger)
        self.dir = "notes"
        os.makedirs(self.dir, exist_ok=True)

    def add(self, text: str) -> str:
        if not text.strip():
            return "Note is empty."
        path = os.path.join(self.dir, "notes.md")
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"- {datetime.now().isoformat(timespec='seconds')}: {text}\n")
            return "Note saved."
        except OSError as e:
            return f"[failed] {e}"
