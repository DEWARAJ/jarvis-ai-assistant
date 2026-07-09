"""Persistent task list stored in memory/tasks.json."""
from __future__ import annotations
import os, json
from datetime import datetime

class TaskManager:
    def __init__(self, memory_dir: str = "memory", logger=None):
        self.logger = logger
        os.makedirs(memory_dir, exist_ok=True)
        self.path = os.path.join(memory_dir, "tasks.json")
        self.tasks = self._load()

    def _load(self) -> list:
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                if self.logger: self.logger.warn("tasks.json unreadable; starting fresh")
        return []

    def _save(self) -> bool:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, indent=2)
            return True
        except OSError as e:
            if self.logger: self.logger.error(f"tasks save failed: {e}")
            return False

    def add(self, title: str, priority: str = "normal") -> dict:
        title = (title or "").strip()
        if not title:
            return {"ok": False, "msg": "Task needs a title."}
        tid = (max((t["id"] for t in self.tasks), default=0) + 1)
        task = {"id": tid, "title": title, "priority": priority,
                "status": "open", "created": datetime.now().isoformat(timespec="seconds")}
        self.tasks.append(task)
        self._save()
        return {"ok": True, "task": task}

    def list(self, status: str | None = None) -> list:
        if status:
            return [t for t in self.tasks if t["status"] == status]
        return list(self.tasks)

    def complete(self, tid: int) -> dict:
        for t in self.tasks:
            if t["id"] == tid:
                t["status"] = "done"
                t["completed"] = datetime.now().isoformat(timespec="seconds")
                self._save()
                return {"ok": True, "task": t}
        return {"ok": False, "msg": f"No task #{tid}."}

    def open_count(self) -> int:
        return len([t for t in self.tasks if t["status"] == "open"])
