"""Three-tier permission model loaded from config/permissions.json."""
from __future__ import annotations
import json, os

class PermissionManager:
    def __init__(self, config_path: str = "config/permissions.json", logger=None):
        self.logger = logger
        self.config_path = config_path
        self.cfg = self._load()

    def _load(self) -> dict:
        try:
            with open(self.config_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            if self.logger: self.logger.warn("permissions.json missing/invalid; using safe defaults")
            return {"allowed": [], "requires_confirmation": [], "forbidden_unless_enabled": [], "enabled_overrides": []}

    def is_allowed(self, action: str) -> bool:
        return action in self.cfg.get("allowed", [])

    def requires_confirmation(self, action: str) -> bool:
        return action in self.cfg.get("requires_confirmation", [])

    def is_forbidden(self, action: str) -> bool:
        return (action in self.cfg.get("forbidden_unless_enabled", [])
                and action not in self.cfg.get("enabled_overrides", []))

    def summary(self) -> dict:
        return {
            "allowed": self.cfg.get("allowed", []),
            "requires_confirmation": self.cfg.get("requires_confirmation", []),
            "forbidden_unless_enabled": self.cfg.get("forbidden_unless_enabled", []),
            "enabled_overrides": self.cfg.get("enabled_overrides", []),
        }
