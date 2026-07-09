"""Loads and serves modular tools from config/tools.json."""
from __future__ import annotations
import json, importlib

class ToolRegistry:
    def __init__(self, config_path: str = "config/tools.json", context=None, logger=None):
        self.logger = logger
        self.context = context or {}
        self.tools = {}
        self._load(config_path)

    def _load(self, config_path: str) -> None:
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, json.JSONDecodeError):
            if self.logger: self.logger.error("tools.json missing/invalid; no tools loaded")
            return
        for name, meta in cfg.items():
            try:
                mod = importlib.import_module(meta["module"])
                cls = getattr(mod, meta["class"])
                self.tools[name] = cls(context=self.context, logger=self.logger)
            except Exception as e:  # never let one bad tool crash the system
                if self.logger: self.logger.error(f"tool '{name}' failed to load: {e}")

    def get(self, name: str):
        return self.tools.get(name)

    def names(self) -> list:
        return sorted(self.tools.keys())
