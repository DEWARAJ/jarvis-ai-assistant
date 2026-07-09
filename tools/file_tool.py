from __future__ import annotations
import os, shutil
from datetime import datetime
from tools.base_tool import BaseTool

class FileTool(BaseTool):
    """Reads files within the project root only. Writes/overwrites/deletes are gated."""
    name = "file"; scope = "project folders only"
    ROOT = os.path.abspath(".")

    def _safe(self, path: str) -> bool:
        full = os.path.abspath(path)
        return full.startswith(self.ROOT)

    def read(self, path: str) -> str:
        if not self._safe(path):
            return "[blocked] Path is outside the project folder."
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except OSError as e:
            return f"[not found] {path} ({e})"

    def backup(self, path: str) -> str:
        if not (self._safe(path) and os.path.exists(path)):
            return "[skip] nothing to back up."
        dst = f"{path}.{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
        try:
            shutil.copy2(path, dst)
            return f"[backup] {dst}"
        except OSError as e:
            return f"[backup failed] {e}"
