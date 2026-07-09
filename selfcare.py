#!/usr/bin/env python3
"""JARVIS scheduled self-upkeep — runs on its own (weekly via Task Scheduler).

Auto-fixes SAFE problems (missing folders, corrupted runtime files), detects missing
optional packages, and checks the repo for updates — then logs and speaks a summary.
It does NOT auto-install packages or pull code; those still require the master's 'confirm'
inside JARVIS. This is self-maintenance on autopilot, with you holding the final yes.
"""
from __future__ import annotations
import os, sys, json, datetime, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def speak(msg: str) -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        ps = ("Add-Type -AssemblyName System.Speech; "
              "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              "$s.Rate = 0; $s.Speak([Console]::In.ReadToEnd())")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], input=msg, text=True, timeout=40)
    except Exception:
        pass


def run() -> str:
    from core.self_improve import SelfImprover
    si = SelfImprover(None)
    heal = si.heal()
    upd = si.check_updates()
    try:
        os.makedirs("logs", exist_ok=True)
        with open(os.path.join("logs", "selfcare.log"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"),
                                "fixed": heal["fixed"], "needs": heal["needs"],
                                "missing_deps": heal["missing_deps"], "update": upd["message"]}) + "\n")
    except Exception:
        pass
    parts = ["JARVIS self-care complete, sir."]
    parts.append(("Repaired " + str(len(heal["fixed"])) + " item(s).") if heal["fixed"] else "Nothing needed repair.")
    if heal["needs"]:
        parts.append("Needs your eye: " + "; ".join(heal["needs"]) + ".")
    if heal["missing_deps"]:
        parts.append("Optional powers not installed: " + ", ".join(heal["missing_deps"]) +
                     " — say 'fix yourself' then 'confirm' to add them.")
    parts.append(upd["message"])
    return " ".join(parts)


def main() -> int:
    summary = run()
    print(summary)
    speak(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
