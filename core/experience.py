"""Episodic memory — JARVIS remembers past tasks and recalls similar ones.

Lightweight and dependency-free: stores each completed goal/plan/outcome to
memory/episodes.json and retrieves the most similar past episodes by keyword overlap
(Jaccard). Not a neural embedding store, but real, offline, and useful — it lets the
planner say "last time you asked something like this, here's what worked."
"""
from __future__ import annotations
import os, json, time, re

_STOP = set("the a an of to and or for in on at is are be do this that with my your me i it as we "
            "how can you please jarvis get make".split())


def _tokens(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in _STOP and len(w) > 2}


class Experience:
    def __init__(self, path: str = "memory/episodes.json", logger=None, cap: int = 200):
        self.path = path
        self.logger = logger
        self.cap = cap
        self.items = self._load()

    def _load(self) -> list:
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.items[-self.cap:], f, indent=2)
        except Exception:
            pass

    def record(self, goal: str, subgoals, outcome: str):
        self.items.append({"goal": goal, "subgoals": subgoals or [], "outcome": (outcome or "")[:600],
                           "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
        self._save()

    def recall(self, goal: str, k: int = 2, threshold: float = 0.12) -> list:
        gt = _tokens(goal)
        if not gt or not self.items:
            return []
        scored = []
        for it in self.items:
            t = _tokens(it.get("goal", ""))
            if not t:
                continue
            j = len(gt & t) / len(gt | t)
            if j >= threshold:
                scored.append((j, it))
        scored.sort(key=lambda x: -x[0])
        return [it for _, it in scored[:k]]
