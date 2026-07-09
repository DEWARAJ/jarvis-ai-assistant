from __future__ import annotations
from tools.base_tool import BaseTool

class TaskTool(BaseTool):
    name = "task"; scope = "memory/tasks.json"
    def _tm(self):
        return self.context.get("tasks")
    def add(self, title): return self._tm().add(title) if self._tm() else {"ok": False}
    def list(self, status=None): return self._tm().list(status) if self._tm() else []
