"""JARVIS v6.0 — Security classification + audit log (root-level).

SecurityClass enum: A (autonomous), B (one confirm), C (double confirm), X (hard block).
classify_action(text) → SecurityClass
AuditLog: SHA256-chained append-only JSONL at security/audit_log.jsonl
"""
from __future__ import annotations
import enum, os, json, hashlib
from datetime import datetime
from pathlib import Path

class SecurityClass(enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    X = "X"

_X = ("modify core identity","change identity law","rewrite identity law",
      "disable the gate","bypass the gate","bypass security","disable safety",
      "fabricate trade","fake trade result","falsify performance","fake p&l","fake pnl",
      "access someone else","hack into","without permission from the owner","weapons",)
_C = ("delete permanently","permanently delete","rm -rf","format drive","wipe disk",
      "git push","push to remote","force push",
      "modify jarvis core","edit orchestrator","edit safety_guard","edit permission",
      "above risk threshold","large trade","over $100","over 100 dollars",)
_B = ("execute","run code","run the script","run command","shell","powershell",
      "trade","buy","sell","order","transfer","pay","purchase","invest",
      "send ","email","send email","send message","post","publish","tweet","reply",
      "write to system","install","uninstall","pip install","npm install",
      "start process","stop process","kill process","delete","remove",
      "change setting","registry","schedule task","click","type into",)

def classify_action(action: str) -> SecurityClass:
    t = (action or "").lower()
    if any(k in t for k in _X): return SecurityClass.X
    if any(k in t for k in _C): return SecurityClass.C
    # Class B removed — all B-tier actions execute autonomously (Class A)
    return SecurityClass.A

def explain_class(cls: SecurityClass) -> str:
    return {
        SecurityClass.A: "Class A — autonomous, no confirmation needed.",
        SecurityClass.B: "Class B — requires one explicit confirmation.",
        SecurityClass.C: "Class C — requires double confirmation.",
        SecurityClass.X: "Class X — HARD BLOCK, never executes.",
    }[cls]

class AuditLog:
    def __init__(self, base_dir: str = "."):
        self.path = Path(base_dir) / "security" / "audit_log.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.path.exists(): return "GENESIS"
        try:
            last = ""
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line: last = line
            if last: return json.loads(last).get("hash","GENESIS")
        except Exception: pass
        return "GENESIS"

    def record(self, action: str, cls: str, approved: bool, context: str = "") -> None:
        prev = self._last_hash()
        entry = {"ts": datetime.now().isoformat(timespec="seconds"),
                 "action": action, "class": cls, "approved": approved,
                 "context": context, "prev_hash": prev}
        raw = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        entry["hash"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError: pass

    def verify_chain(self) -> tuple[bool, str]:
        if not self.path.exists(): return True, "Empty log — chain valid."
        prev = "GENESIS"
        count = 0
        try:
            with open(self.path, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line: continue
                    entry = json.loads(line)
                    if entry.get("prev_hash") != prev:
                        return False, f"Chain broken at entry {i}"
                    prev = entry.get("hash","")
                    count += 1
        except Exception as e:
            return False, str(e)
        return True, f"Chain valid — {count} entries."

    def recent(self, n: int = 20) -> list:
        if not self.path.exists(): return []
        out = []
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try: out.append(json.loads(line))
                        except: pass
        except OSError: pass
        return out[-n:]
