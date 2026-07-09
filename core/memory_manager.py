"""Structured local JSON memory. Never stores secrets."""
from __future__ import annotations
import os, json, re
from datetime import datetime

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*\S+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]

CATEGORIES = [
    "user_profile", "business_profile", "active_projects", "products",
    "brand_voice", "customer_support_knowledge", "marketing_tactics",
    "ecommerce_rules", "automation_rules", "trading_journal", "watchlists",
    "task_history", "decisions", "preferences", "daily_routine", "safety_rules",
]

class MemoryManager:
    def __init__(self, memory_dir: str = "memory", logger=None):
        self.memory_dir = memory_dir
        self.logger = logger
        os.makedirs(memory_dir, exist_ok=True)
        self.path = os.path.join(memory_dir, "memory.json")
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                if self.logger: self.logger.warn("memory.json unreadable; starting fresh")
        return {c: [] for c in CATEGORIES}

    def _save(self) -> bool:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            return True
        except OSError as e:
            if self.logger: self.logger.error(f"memory save failed: {e}")
            return False

    @staticmethod
    def looks_like_secret(text: str) -> bool:
        return any(p.search(text) for p in SECRET_PATTERNS)

    def remember(self, category: str, content: str) -> dict:
        if category not in CATEGORIES:
            return {"ok": False, "msg": f"Unknown memory category '{category}'."}
        if self.looks_like_secret(content):
            if self.logger: self.logger.warn("Refused to store suspected secret.")
            return {"ok": False, "msg": "Refused: content looks like a password/API key. Secrets are never stored."}
        entry = {"content": content, "ts": datetime.now().isoformat(timespec="seconds")}
        self.data.setdefault(category, []).append(entry)
        ok = self._save()
        return {"ok": ok, "msg": f"Remembered in {category}." if ok else "Save failed (logged)."}

    def recall(self, category: str) -> list:
        return self.data.get(category, [])

    def forget(self, category: str) -> dict:
        if category in self.data:
            self.data[category] = []
            self._save()
            return {"ok": True, "msg": f"Cleared {category}."}
        return {"ok": False, "msg": "Category not found."}

    def overview(self) -> dict:
        return {c: len(v) for c, v in self.data.items()}
