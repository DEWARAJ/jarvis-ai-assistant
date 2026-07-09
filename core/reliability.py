"""Reliability layer — self-verifying actions, honest retry, and outcome logging.

JARVIS's promise is that it never fakes success. This module wraps an action so that:
  - the result is checked for failure markers,
  - safe (read-only / idempotent) actions are retried once on a transient failure,
  - every outcome is logged to logs/actions.log,
  - and an honest result is always returned (the failure text is preserved, never hidden).
"""
from __future__ import annotations
import os, json, time, datetime

# Failure markers JARVIS uses in its honest replies. If a result contains one, the action
# is treated as not-yet-verified.
_FAIL_MARKERS = (
    "[!]", "couldn't", "could not", "i couldn't", "failed", "unable", "try again",
    "is unavailable", "not available just now", "couldn't reach", "can't reach",
    "cannot reach", "couldn't get", "isn't available", "no readable text", "timed out",
    "unreachable", "went wrong", "i can't find", "not found",
)

# Actions that are safe to retry automatically (reads / lookups — no harmful side effects,
# no second window opened). Side-effecting actions (open_app, volume, delete…) are NEVER
# blind-retried; they are run once and verified.
RETRIABLE_ACTIONS = {
    "research", "news", "weather", "price", "read_url", "market_briefing",
    "situation", "daily_briefing", "advise", "improve", "check_in",
    "check_email", "unread_email", "system_info",
}


def looks_failed(result) -> bool:
    if result is None:
        return True
    t = str(result).strip().lower()
    if not t:
        return True
    return any(m in t for m in _FAIL_MARKERS)


def log_action(action: str, ok: bool, attempts: int, snippet, path: str = "logs/actions.log") -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.datetime.now().isoformat(timespec="seconds"),
                "action": action, "ok": bool(ok), "attempts": int(attempts),
                "snippet": str(snippet)[:160],
            }) + "\n")
    except Exception:
        pass


class ActionOutcome:
    __slots__ = ("ok", "result", "attempts", "error")

    def __init__(self, ok: bool, result, attempts: int = 1, error: str = ""):
        self.ok = ok
        self.result = result
        self.attempts = attempts
        self.error = error

    def __repr__(self):
        return f"<ActionOutcome ok={self.ok} attempts={self.attempts}>"


def attempt(fn, failed_check=looks_failed, retries: int = 1, delay: float = 0.4,
            label: str = "", logger=None, log: bool = True) -> ActionOutcome:
    """Run fn(); if the result looks failed (or it raises), retry up to `retries` more times.
    Returns an ActionOutcome; the failing result is preserved (honest reporting)."""
    last = None
    err = ""
    for i in range(retries + 1):
        try:
            res = fn()
            if not failed_check(res):
                if log:
                    log_action(label, True, i + 1, res)
                return ActionOutcome(True, res, i + 1)
            last = res
        except Exception as e:
            err = str(e)
            last = f"[!] {e}"
            if logger:
                logger.error(f"action '{label}' raised: {e}")
        if i < retries and delay:
            time.sleep(delay)
    if log:
        log_action(label, False, retries + 1, last)
    return ActionOutcome(False, last, retries + 1, err)
