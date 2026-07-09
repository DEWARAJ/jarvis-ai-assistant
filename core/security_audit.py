"""JARVIS v3.0 — military-grade security classification + tamper-evident audit log.

Two pieces:
  * SecurityClassifier — maps an action description to a class:
        A  autonomous (no ask)         B  one confirmation
        C  double confirmation         X  HARD BLOCK (never executes)
    This is advisory routing on top of the existing SafetyGuard/permission tiers; it does
    not replace them — it adds the C (double-confirm) and X (hard-block) layers v3 demands.
  * AuditLog — append-only security/audit_log.jsonl with a SHA256 hash chain. Each entry
    carries prev_hash + its own hash so any later edit/deletion breaks the chain (tamper-evident).

Never raises on I/O. Classification is keyword heuristics — deliberately conservative
(when unsure, escalate up, never down).
"""
from __future__ import annotations
import os, json, hashlib
from datetime import datetime

# ---- classification signals (escalate-up when ambiguous) ----
_X_BLOCK = (
    "modify core identity", "change identity law", "rewrite identity law",
    "disable the gate", "bypass the gate", "bypass security", "disable safety",
    "fabricate trade", "fake trade result", "falsify performance", "fake p&l", "fake pnl",
    "access someone else", "hack into", "without permission from the owner",
)
_C_DOUBLE = (
    "delete permanently", "permanently delete", "rm -rf", "format drive", "wipe disk",
    "git push", "push to remote", "force push",
    "modify jarvis core", "edit orchestrator", "edit safety_guard", "edit permission",
    "above risk threshold", "large trade", "over $100", "over 100 dollars",
)
_B_CONFIRM = (
    "execute", "run code", "run the script", "run command", "shell", "powershell",
    "trade", "buy", "sell", "order", "transfer", "pay", "purchase", "invest",
    "send ", "email", "send email", "send message", "post", "publish", "tweet", "reply",
    "write to system", "install", "uninstall", "pip install", "npm install",
    "start process", "stop process", "kill process", "delete", "remove",
    "change setting", "registry", "schedule task",
)


class SecurityClassifier:
    @staticmethod
    def classify(action: str) -> str:
        t = (action or "").lower()
        if any(k in t for k in _X_BLOCK):
            return "X"
        if any(k in t for k in _C_DOUBLE):
            return "C"
        # Class B removed — B-tier actions execute autonomously (Class A)
        return "A"

    @staticmethod
    def explain(cls: str) -> str:
        return {
            "A": "Class A — autonomous, executes without asking.",
            "B": "Class B — requires one explicit confirmation.",
            "C": "Class C — requires double confirmation (type the action name + 'confirm').",
            "X": "Class X — HARD BLOCK, never executes regardless of instruction.",
        }.get(cls, "Unknown class.")


class AuditLog:
    """Append-only, SHA256-chained audit trail for Class B/C/X actions."""

    def __init__(self, base_dir=".", logger=None):
        self.logger = logger
        self.dir = os.path.join(base_dir, "security")
        os.makedirs(self.dir, exist_ok=True)
        self.path = os.path.join(self.dir, "audit_log.jsonl")

    def _last_hash(self) -> str:
        last = "GENESIS"
        if not os.path.exists(self.path):
            return last
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        last = json.loads(line).get("hash", last)
                    except Exception:
                        continue
        except OSError:
            pass
        return last

    @staticmethod
    def _hash(prev_hash: str, core: dict) -> str:
        raw = prev_hash + json.dumps(core, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()

    def record(self, action: str, cls: str, result: str,
               authorized_by: str = "Dew", reversible: bool = True) -> dict:
        prev = self._last_hash()
        core = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "action": (action or "")[:500],
            "class": cls,
            "authorized_by": authorized_by,
            "result": (result or "")[:500],
            "reversible": bool(reversible),
            "prev_hash": prev,
        }
        core["hash"] = self._hash(prev, {k: core[k] for k in core if k != "hash"})
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(core, ensure_ascii=False) + "\n")
        except OSError as e:
            if self.logger:
                self.logger.warn(f"audit write failed: {e}")
        return core

    def verify(self) -> dict:
        """Walk the chain; report whether it is intact and where it breaks."""
        if not os.path.exists(self.path):
            return {"ok": True, "entries": 0, "note": "no audit log yet"}
        prev = "GENESIS"
        n = 0
        try:
            with open(self.path, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    e = json.loads(line)
                    n += 1
                    core = {k: e[k] for k in ("ts", "action", "class", "authorized_by",
                                              "result", "reversible", "prev_hash") if k in e}
                    if e.get("prev_hash") != prev:
                        return {"ok": False, "entries": n, "broken_at": i, "reason": "prev_hash mismatch"}
                    if self._hash(prev, core) != e.get("hash"):
                        return {"ok": False, "entries": n, "broken_at": i, "reason": "hash mismatch (tampered)"}
                    prev = e["hash"]
        except (OSError, json.JSONDecodeError, KeyError) as ex:
            return {"ok": False, "entries": n, "reason": f"read error: {ex}"}
        return {"ok": True, "entries": n, "note": "chain intact"}

    def recent(self, n=10) -> list:
        out = []
        if not os.path.exists(self.path):
            return out
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            out.append(json.loads(line))
                        except Exception:
                            continue
        except OSError:
            pass
        return out[-n:]
