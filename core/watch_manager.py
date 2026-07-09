"""Watch Manager — JARVIS's proactive eyes on the world.

Registers "watches" that JARVIS checks on a background loop and surfaces an alert when a
condition is met — before the master asks. All watchers are READ-ONLY (Tier 1): prices,
system health, news topics, and web-page changes. No actions, no trades, ever.

Data comes from injected providers so this module is decoupled and fully testable:
  providers = {
    "price":  fn(symbol) -> float | None,
    "system": fn() -> {"cpu":%, "memory":%, "disk":%, "battery":% | None},
    "news":   fn(topic) -> [headline, ...],
    "url":    fn(url) -> page_text,
  }
"""
from __future__ import annotations
import os, json, time, hashlib, datetime


class WatchManager:
    def __init__(self, providers: dict | None = None, path: str = "memory/watches.json",
                 logger=None, cooldown: int = 1800):
        self.providers = providers or {}
        self.path = path
        self.logger = logger
        self.cooldown = cooldown
        self.watches = self._load()
        self._next_id = (max([w["id"] for w in self.watches], default=0) + 1)

    # ---- persistence ----
    def _load(self) -> list:
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return []
        return []

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.watches, f, indent=2)
        except OSError:
            pass

    # ---- CRUD ----
    def add(self, kind: str, target: str, op: str = "", value=None) -> dict:
        w = {"id": self._next_id, "kind": kind, "target": target, "op": op, "value": value,
             "active": True, "last_value": None, "cooldown_until": 0, "fires": 0,
             "created": datetime.datetime.now().isoformat(timespec="seconds")}
        self._next_id += 1
        self.watches.append(w)
        self._save()
        return w

    def remove(self, wid: int = None, target: str = "") -> int:
        before = len(self.watches)
        if wid is not None:
            self.watches = [w for w in self.watches if w["id"] != wid]
        elif target:
            t = target.lower()
            self.watches = [w for w in self.watches if t not in str(w["target"]).lower()]
        self._save()
        return before - len(self.watches)

    def clear(self) -> int:
        n = len(self.watches)
        self.watches = []
        self._save()
        return n

    def list(self) -> list:
        return list(self.watches)

    def summary(self) -> str:
        if not self.watches:
            return "I'm not monitoring anything yet, sir. Try 'monitor btc below 50000', 'monitor disk', or 'watch news about AI'."
        lines = ["Currently monitoring, sir:"]
        for w in self.watches:
            cond = ""
            if w["kind"] == "price":
                cond = (f" {w['op']} {w['value']:,}" if w["op"] in ("<", ">") and w["value"] is not None
                        else f" ±{w['value']}% move")
            elif w["kind"] == "system":
                cond = f" {w['op']} {w['value']}%"
            lines.append(f"  #{w['id']} {w['kind']}: {w['target']}{cond}" + ("" if w["active"] else " (paused)"))
        return "\n".join(lines)

    # ---- evaluation ----
    def _provider(self, kind):
        return self.providers.get(kind)

    def check_one(self, w: dict):
        """Return (fired: bool, message: str|None). Updates w's baseline state."""
        kind = w["kind"]
        prov = self._provider(kind)
        if not prov:
            return (False, None)
        try:
            if kind == "price":
                price = prov(w["target"])
                if price is None:
                    return (False, None)
                op, val = w["op"], w["value"]
                if op == "<" and val is not None and price < val:
                    w["last_value"] = price
                    return (True, f"Watch alert, sir — {w['target'].upper()} is at {price:,.2f}, below your {val:,.2f} mark.")
                if op == ">" and val is not None and price > val:
                    w["last_value"] = price
                    return (True, f"Watch alert, sir — {w['target'].upper()} is at {price:,.2f}, above your {val:,.2f} mark.")
                if op == "chg":
                    base = w["last_value"]
                    if base is None:
                        w["last_value"] = price
                        return (False, None)
                    if base and abs(price - base) / base * 100.0 >= (val or 5):
                        move = (price - base) / base * 100.0
                        w["last_value"] = price
                        return (True, f"Watch alert, sir — {w['target'].upper()} has moved {move:+.1f}% to {price:,.2f}.")
                w["last_value"] = price
                return (False, None)

            if kind == "system":
                s = prov() or {}
                val = s.get(w["target"])
                if val is None:
                    return (False, None)
                op, thr = w["op"], w["value"]
                if op == "<" and val < thr:
                    return (True, f"System watch, sir — {w['target']} is at {val:.0f}%, below {thr:g}%.")
                if op == ">" and val > thr:
                    return (True, f"System watch, sir — {w['target']} is at {val:.0f}%, above {thr:g}%.")
                return (False, None)

            if kind == "news":
                heads = prov(w["target"]) or []
                if not heads:
                    return (False, None)
                top = heads[0]
                if w["last_value"] is None:
                    w["last_value"] = top
                    return (False, None)  # arm silently on first sight
                if top != w["last_value"]:
                    w["last_value"] = top
                    return (True, f"News on {w['target']}, sir: {top}")
                return (False, None)

            if kind == "url":
                text = prov(w["target"]) or ""
                if not text:
                    return (False, None)
                h = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
                if w["last_value"] is None:
                    w["last_value"] = h
                    return (False, None)
                if h != w["last_value"]:
                    w["last_value"] = h
                    return (True, f"The page {w['target']} has changed, sir.")
                return (False, None)
        except Exception as e:
            if self.logger:
                self.logger.error(f"watch {w.get('id')} check failed: {e}")
        return (False, None)

    def check_all(self) -> list:
        """Check every active, off-cooldown watch. Returns alert messages; persists state."""
        now = time.time()
        msgs = []
        changed = False
        for w in self.watches:
            if not w.get("active"):
                continue
            if now < w.get("cooldown_until", 0):
                continue
            fired, msg = self.check_one(w)
            changed = True  # baselines may have updated
            if fired and msg:
                w["fires"] = w.get("fires", 0) + 1
                if w["kind"] in ("price", "system"):
                    w["cooldown_until"] = now + self.cooldown
                msgs.append(msg)
        if changed:
            self._save()
        return msgs
