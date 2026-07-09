"""JARVIS OS - Security & Safety Guard (hardened).

Three-tier safety model:
  TIER 1 ALLOWED: executes immediately, logged.
  TIER 2 CONFIRM: shown to Master for explicit yes/no, never auto-runs.
  TIER 3 FORBIDDEN: hard block, cannot be bypassed from within a session.

Additional layers:
  Injection detection: catches prompt-injection attempts inside user text.
  Threat scoring: escalates repeated suspicious patterns per session.
  Audit trail: every safety decision written to logs/audit.log.
"""
from __future__ import annotations
import json, os, datetime
from typing import Optional

_DESTRUCTIVE = {
    "delete", "rm ", "remove", "format", "overwrite",
    "drop ", "wipe", "truncate", "destroy", "erase",
    "uninstall", "factory reset",
}

_INJECTION_SIGNALS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard your",
    "new system prompt",
    "override your",
    "forget your training",
    "forget your rules",
    "you have no restrictions",
    "you have no limits",
    "bypass safety",
    "bypass all",
    "jailbreak",
    "do anything now",
    "dan mode",
    "developer mode",
    "god mode",
    "unrestricted mode",
]


class SafetyReview:
    __slots__ = ("allowed", "tier", "reason", "warnings", "threat_level")

    def __init__(self, allowed: bool, tier: str, reason: str,
                 warnings: Optional[list] = None, threat_level: int = 0):
        self.allowed = allowed
        self.tier = tier
        self.reason = reason
        self.warnings = warnings or []
        self.threat_level = threat_level

    def __repr__(self) -> str:
        return "<SafetyReview tier=" + self.tier + " allowed=" + str(self.allowed) + " threat=" + str(self.threat_level) + ">"


class SafetyGuard:
    def __init__(self, permission_manager, logger=None):
        self.pm = permission_manager
        self.logger = logger
        self._session_threat_score = 0
        self._blocked_count = 0
        self._audit_path = os.path.join("logs", "audit.log")
        os.makedirs("logs", exist_ok=True)

    def review(self, action: str, raw_text: str = "") -> SafetyReview:
        text_lower = (raw_text or "").lower()
        warnings: list = []

        # Layer 0: Injection detection
        injection = self._detect_injection(text_lower)
        if injection:
            self._session_threat_score += 10
            self._blocked_count += 1
            reason = "Possible prompt-injection detected: '" + injection + "'. Incident logged."
            r = SafetyReview(False, "forbidden", reason, threat_level=3)
            self._audit("INJECTION_BLOCKED", action, raw_text, reason)
            if self.logger:
                self.logger.warn("[SECURITY] Injection: '" + injection + "'")
            return r

        # Layer 1: Hard-forbidden
        if self.pm.is_forbidden(action):
            self._session_threat_score += 1
            self._blocked_count += 1
            reason = "'" + action + "' is hard-forbidden. Enable in MASTER_PERMISSIONS first."
            r = SafetyReview(False, "forbidden", reason, threat_level=2)
            self._audit("FORBIDDEN", action, raw_text, reason)
            if self.logger:
                self.logger.warn("[GATE-FORBIDDEN] " + action)
            return r

        # Layer 2: Requires confirmation
        if self.pm.requires_confirmation(action):
            if any(k in text_lower for k in _DESTRUCTIVE):
                warnings.append("Destructive keyword detected - backup recommended before proceeding.")
            reason = "'" + action + "' requires explicit Master approval."
            r = SafetyReview(False, "requires_confirmation", reason, warnings, threat_level=1)
            self._audit("HELD_FOR_CONFIRM", action, raw_text, reason)
            if self.logger:
                self.logger.info("[GATE-CONFIRM] " + action)
            return r

        # Layer 3: Allowed
        if any(k in text_lower for k in _DESTRUCTIVE):
            warnings.append("Destructive keyword in request - proceeding with extra care.")
        if self._session_threat_score >= 5:
            warnings.append("Advisory: " + str(self._session_threat_score) + " threat points this session. Review logs/audit.log.")

        r = SafetyReview(True, "allowed", "Within permitted actions.", warnings, threat_level=0)
        self._audit("ALLOWED", action, raw_text, "ok")
        return r

    def _detect_injection(self, text_lower: str) -> str:
        for signal in _INJECTION_SIGNALS:
            if signal in text_lower:
                return signal
        return ""

    def _audit(self, verdict: str, action: str, raw: str, reason: str) -> None:
        try:
            ts = datetime.datetime.now().isoformat(timespec="seconds")
            entry = {
                "ts": ts, "verdict": verdict, "action": action,
                "threat_score": self._session_threat_score,
                "raw_snippet": (raw or "")[:120],
                "reason": reason,
            }
            with open(self._audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def session_summary(self) -> str:
        return "Security session: threat_score=" + str(self._session_threat_score) + ", blocked=" + str(self._blocked_count) + "."

    def reset_session(self) -> None:
        self._session_threat_score = 0
        self._blocked_count = 0
