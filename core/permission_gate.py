"""Authoritative permission gate — the ONE place that decides an action's class.

Phase-1 hardening reconciliation. The audit found three disagreeing permission
vocabularies (TIER 1/2/3 in the persona + permissions.json, CLASS A/B in the
governance prompt, and an ad-hoc self.pending+confirm flow) and that the documented
SafetyGuard/_gate() path was effectively DEAD on execution. This module collapses the
model into a single classifier keyed on the REAL dispatch intent names.

Classes:
  CLASS_A   — reversible / read / compute / draft. Auto-executes, reported after.
  CLASS_B   — externally-visible, financial, system-altering, or permanently
              destructive. Confirm once before running. NEVER auto-runs.
  FORBIDDEN — structurally disallowed at runtime; no confirmation can override it.
              Specifically: JARVIS editing its own core / permission-enforcing source.

Design rule: phrasing NEVER changes the class. The class is a property of what the
action DOES, decided here, not of how the master worded it (defends BUG 4).
"""
from __future__ import annotations
import os

CLASS_A = "A"
CLASS_B = "B"
CLASS_C = "C"          # master double-confirmation (self-modification, v10.0)
FORBIDDEN = "FORBIDDEN"

# Per operator decision: only the catastrophic / irreversible actions stay confirm-gated —
# permanent deletion and anything financial or externally-sent. Everything else (general
# shell, installs, git pulls, power, paper trading, file moves) now auto-executes.
CLASS_B_INTENTS = {
    "delete_files",       # permanent deletion — always confirm
}

# Financial + external-send actions: always confirm, even once wired.
CLASS_B_FUTURE = {
    "send_email", "place_trade", "spend_money",
}
CLASS_B_INTENTS |= CLASS_B_FUTURE

# Core / permission-enforcing source files. JARVIS may PROPOSE changes to these
# (written to a separate review file) but may never edit them itself at runtime.
PROTECTED_SOURCE = (
    "orchestrator.py", "reasoning_core.py", "agentic_core.py",
    "permission_manager.py", "permission_gate.py", "safety_guard.py",
)

# Shell-side write/edit verbs that, aimed at protected source, count as self-modification.
_WRITE_HINTS = ("> core", ">core", "set-content", "out-file", "add-content",
                "del core", "rm core", "remove-item", "edit ", "sed -i",
                "open(", ".write(", "tee core")


def is_self_modification(action: str, arg: str = "") -> bool:
    """True if the action would edit/delete JARVIS's own core or permission source.
    Structural FORBIDDEN — enforced regardless of confirmation (Phase 3 boundary)."""
    a = (action or "").strip()
    low = (arg or "").lower()
    if a == "self_code":
        return True
    touches_protected = any(p in low for p in PROTECTED_SOURCE)
    if a in ("delete_files", "write_code", "run_command") and touches_protected:
        if a == "run_command":
            return any(h in low for h in _WRITE_HINTS) or (">" in low)
        return True
    return False


# Benign launchers — opening a viewer/editor or a document is reversible (Class A).
# Launching an app/file is Tier-1 in the persona; only destructive shell stays Class B.
_SAFE_LAUNCHERS = ("notepad", "notepad.exe", "notepad++", "notepad++.exe", "wordpad",
                   "write", "explorer", "explorer.exe", "code", "code.exe", "start")
_DOC_EXTS = (".txt", ".md", ".pdf", ".doc", ".docx", ".csv", ".log", ".json",
             ".rtf", ".xlsx", ".pptx", ".html", ".png", ".jpg", ".jpeg")
# If any of these appear, it is NOT a benign launch — keep it Class B.
_LAUNCH_DANGER = ("&", "|", ";", "&&", "del ", "rm ", "format", "reg ", "rmdir",
                  "rd ", "-enc", "encodedcommand", "shutdown", "diskpart", "cipher /w",
                  "vssadmin", "schtasks", "net user", "takeown", "icacls", "/c ", "/k ",
                  "invoke-", "iex", "curl ", "wget ", "bitsadmin")


def _is_benign_launch(arg: str) -> bool:
    """True if the run_command just opens a file or a known viewer/editor — no shell danger."""
    low = (arg or "").strip().lower()
    if not low or any(h in low for h in _LAUNCH_DANGER):
        return False
    first = low.split()[0].strip('"').strip("'")
    if first in _SAFE_LAUNCHERS:
        return True
    # Directly opening a document file (e.g. "...\\report.txt")
    head = low.split('"')[1] if low.startswith('"') and '"' in low[1:] else low.split()[0]
    return head.strip('"').strip("'").endswith(_DOC_EXTS) or low.endswith(_DOC_EXTS)


# Even with general shell freed, a command that DELETES or WIPES data stays confirm-gated
# (operator kept "delete" protected). This catches deletion via run_command too.
_DESTRUCTIVE_SHELL = ("del ", "del.", "erase ", " rm ", "rm -", "rmdir", " rd ", "remove-item",
                      "format ", "diskpart", "cipher /w", "vssadmin delete", "rd /s",
                      "del /", "deltree", "format/", " /f /q")


def _is_destructive_shell(arg: str) -> bool:
    low = " " + (arg or "").strip().lower() + " "
    return any(h in low for h in _DESTRUCTIVE_SHELL)


def classify(action: str, arg: str = "") -> tuple[str, str]:
    """Return (class, reason). The single authoritative decision for an action."""
    a = (action or "").strip()
    if is_self_modification(a, arg):
        # v10.0: self-modification is Class C — allowed with the master's DOUBLE confirmation
        # (say 'yes', then type 'modify'). Backup + smoke-test + auto-rollback still apply.
        # NOTE: modifying the CORE IDENTITY LAWS or bypassing security stays Class X /
        # hard-blocked in the orchestrator's SecurityClassifier — this downgrade covers only
        # editing JARVIS's own source files.
        return (CLASS_C,
                "Self-modification is a Class C action, sir — editing my own core/permission "
                "source. It needs your double confirmation: say 'yes', then type 'modify' to "
                "authorise. I will back up first, smoke-test after, and auto-rollback on failure.")
    # Opening a file/app in a viewer or editor is Class A (reversible, Tier-1).
    if a == "run_command" and _is_benign_launch(arg):
        return (CLASS_A, "Class A: opening a file or app in a viewer/editor — auto-executes.")
    # General shell is freed, but deletion/wipe commands stay confirm-gated.
    if a == "run_command" and _is_destructive_shell(arg):
        return (CLASS_B, "Class B: this command deletes or wipes data — confirm first, sir.")
    if a in CLASS_B_INTENTS:
        return (CLASS_B, f"'{a}' is a Class B action (external, financial, system-altering, "
                         "or destructive) and requires your explicit confirmation.")
    return (CLASS_A, "Class A: reversible / read / compute / draft — auto-executes.")


def is_class_b(action: str, arg: str = "") -> bool:
    return classify(action, arg)[0] == CLASS_B


def is_forbidden(action: str, arg: str = "") -> bool:
    return classify(action, arg)[0] == FORBIDDEN
