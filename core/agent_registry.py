"""Loads and serves specialist sub-agents from config/agents.json."""
from __future__ import annotations
import json, importlib

class AgentRegistry:
    def __init__(self, config_path: str = "config/agents.json", context=None, logger=None):
        self.logger = logger
        self.context = context or {}
        self.agents = {}
        self.meta = {}
        self._load(config_path)

    def _load(self, config_path: str) -> None:
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, json.JSONDecodeError):
            if self.logger: self.logger.error("agents.json missing/invalid; no agents loaded")
            return
        for name, m in cfg.items():
            self.meta[name] = m
            try:
                mod = importlib.import_module(m["module"])
                cls = getattr(mod, m["class"])
                self.agents[name] = cls(name=name, context=self.context, logger=self.logger)
            except Exception as e:
                if self.logger: self.logger.error(f"agent '{name}' failed to load: {e}")

    def get(self, name: str):
        return self.agents.get(name)

    def names(self) -> list:
        return sorted(self.agents.keys())

    def describe(self) -> list:
        return [{"name": n, "scope": self.meta.get(n, {}).get("scope", ""),
                 "risk": self.meta.get(n, {}).get("risk", "")} for n in self.names()]
