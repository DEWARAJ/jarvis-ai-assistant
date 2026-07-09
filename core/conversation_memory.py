"""Persistent conversation memory — every turn logged to disk and recallable across sessions.

The orchestrator's in-RAM `history` is lost on restart. This gives JARVIS a durable, append-only
transcript (one JSON object per line in memory/conversations.jsonl) so it can:
  * SEED context on boot (so it 'remembers' the last conversation after a restart), and
  * RECALL / SEARCH past conversations on command ('what did we talk about', 'recall our chat
    about the trading bot').

Secrets are redacted before anything is written (same posture as MemoryManager — keys/passwords
are never persisted). Append-only JSONL keeps writes O(1) and survives partial-line corruption.
"""
from __future__ import annotations
import os, json, re
from datetime import datetime

_SECRET = [
    # API keys: sk-..., sk-ant-api03-..., sk-proj-... (hyphens/underscores allowed inside).
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\b(?:pplx|gsk|nvapi|AIza)[A-Za-z0-9_-]{12,}"),   # perplexity/groq/nvidia/google
    re.compile(r"(?i)(api[_-]?key|secret|password|passwd|token|bearer)\s*[:=]?\s*\S{6,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),                  # github tokens
]


def _redact(text: str) -> str:
    t = text or ""
    for p in _SECRET:
        t = p.sub("[redacted]", t)
    return t


class ConversationMemory:
    """Durable transcript log + recall. Persists across restarts; redacts secrets on write."""

    def __init__(self, memory_dir: str = "memory", logger=None, keep_context: int = 20):
        self.logger = logger
        self.keep_context = keep_context          # turns re-loaded into context on boot
        os.makedirs(memory_dir, exist_ok=True)
        self.path = os.path.join(memory_dir, "conversations.jsonl")

    # ---- write ----
    def log_turn(self, user: str, reply: str) -> None:
        """Append one (user, reply) turn. Skips empty/superseded turns. Never raises."""
        if not (user or "").strip() or not (reply or "").strip():
            return
        entry = {"ts": datetime.now().isoformat(timespec="seconds"),
                 "user": _redact(user)[:4000], "reply": _redact(reply)[:4000]}
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            if self.logger:
                self.logger.warn(f"conversation log write failed: {e}")

    # ---- read ----
    def _read_all(self) -> list:
        out = []
        if not os.path.exists(self.path):
            return out
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        continue          # tolerate a partial/corrupt trailing line
        except OSError:
            pass
        return out

    def recent_turns(self, n: int = 8) -> list:
        return self._read_all()[-max(1, n):]

    def load_history(self) -> list:
        """Recent turns as orchestrator history [{'role','content'},...], to seed context on boot
        so JARVIS continues the previous conversation after a restart."""
        hist = []
        for e in self.recent_turns(self.keep_context):
            if e.get("user"):
                hist.append({"role": "user", "content": e["user"]})
            if e.get("reply"):
                hist.append({"role": "assistant", "content": e["reply"]})
        return hist

    def search(self, query: str, limit: int = 6) -> list:
        q = (query or "").lower().strip()
        if not q:
            return []
        hits = [e for e in self._read_all()
                if q in (e.get("user", "") + " " + e.get("reply", "")).lower()]
        return hits[-limit:]

    def count(self) -> int:
        return len(self._read_all())

    def clear(self) -> int:
        n = self.count()
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
        except OSError as e:
            if self.logger:
                self.logger.warn(f"conversation clear failed: {e}")
        return n
