"""Self-improvement engine — JARVIS fixes, updates, and reviews itself (safely).

The honest, safe version of "self-improving AI":
  - heal(): auto-fixes SAFE problems (missing folders, corrupted runtime JSON), detects
    missing optional packages, and checks its own config — never overwriting your settings.
  - check_updates(): looks for new versions from the project's git repository.
  - improvement_plan(): reviews its own reliability and proposes concrete next upgrades.

What it deliberately does NOT do: download and execute code from the internet on its own.
Installing packages and pulling updates are real, network/system-changing actions, so they
run ONLY behind the master's explicit confirmation (the orchestrator's confirm flow).
"""
from __future__ import annotations
import os, json, shutil, subprocess, sys, importlib


_OPTIONAL_DEPS = ["pyautogui", "pycaw", "psutil", "PIL", "playwright", "uiautomation", "mss"]
_DEP_PIP = {"PIL": "pillow"}
_RUNTIME_JSON = ["memory/tasks.json", "memory/episodes.json", "memory/watches.json"]
_DIRS = ["memory", "logs", "notes", "briefs", "screenshots", "business_knowledge"]


class SelfImprover:
    def __init__(self, orch):
        self.orch = orch

    # ---- detection ----
    def missing_deps(self) -> list:
        miss = []
        for d in _OPTIONAL_DEPS:
            try:
                importlib.import_module(d)
            except Exception:
                miss.append(_DEP_PIP.get(d, d))
        return miss

    def _ensure_dirs(self) -> list:
        fixed = []
        for d in _DIRS:
            if not os.path.isdir(d):
                try:
                    os.makedirs(d, exist_ok=True)
                    fixed.append(f"created missing folder '{d}'")
                except Exception:
                    pass
        return fixed

    def _repair_files(self) -> tuple:
        """Repair only CORRUPTED runtime JSON (back it up first). Returns (fixed, needs)."""
        fixed, needs = [], []
        for f in _RUNTIME_JSON:
            if not os.path.exists(f):
                continue
            try:
                with open(f, encoding="utf-8") as fh:
                    json.load(fh)
            except Exception:
                try:
                    shutil.copy(f, f + ".bak")
                    with open(f, "w", encoding="utf-8") as fh:
                        fh.write("[]")
                    fixed.append(f"repaired corrupted {os.path.basename(f)} (backup at {os.path.basename(f)}.bak)")
                except Exception as e:
                    needs.append(f"couldn't repair {f} ({e})")
        # config sanity (never auto-overwrite the master's settings)
        try:
            with open("config/settings.json", encoding="utf-8") as fh:
                json.load(fh)
        except Exception:
            needs.append("config/settings.json is invalid JSON — I won't overwrite it without you, sir")
        return fixed, needs

    # ---- heal ----
    def heal(self) -> dict:
        fixed = self._ensure_dirs()
        rf, needs = self._repair_files()
        fixed += rf
        return {"fixed": fixed, "needs": needs, "missing_deps": self.missing_deps()}

    # ---- updates from the internet (git) ----
    def check_updates(self) -> dict:
        if not os.path.isdir(".git"):
            return {"is_git": False, "behind": 0,
                    "message": ("This isn't a git checkout, sir, so I can't pull updates directly. "
                                "Clone the project with git and I'll keep it current for you.")}
        try:
            subprocess.run(["git", "fetch"], capture_output=True, text=True, timeout=30)
            r = subprocess.run(["git", "rev-list", "--count", "HEAD..@{u}"],
                               capture_output=True, text=True, timeout=15)
            n = int((r.stdout or "0").strip() or "0")
            if n > 0:
                return {"is_git": True, "behind": n, "message": f"{n} update(s) are available from the repository, sir."}
            return {"is_git": True, "behind": 0, "message": "I'm fully up to date, sir."}
        except Exception as e:
            return {"is_git": True, "behind": 0, "message": f"I couldn't check for updates just now ({e})."}

    # ---- confirmed actions (run only via the orchestrator's confirm flow) ----
    def do_install(self, pkgs: list) -> str:
        pkgs = [p for p in (pkgs or []) if p]
        if not pkgs:
            return "Nothing to install, sir."
        try:
            r = subprocess.run([sys.executable, "-m", "pip", "install", *pkgs],
                               capture_output=True, text=True, timeout=600)
            ok = r.returncode == 0
            tail = (r.stdout or r.stderr or "").strip().splitlines()[-1:] or [""]
            return ("Installed " + ", ".join(pkgs) + ", sir. Restart me to use the new powers." if ok
                    else "The install didn't fully succeed, sir: " + tail[0])
        except Exception as e:
            return f"I couldn't run the install, sir ({e})."

    def do_git_pull(self) -> str:
        try:
            r = subprocess.run(["git", "pull", "--ff-only"], capture_output=True, text=True, timeout=120)
            out = (r.stdout or r.stderr or "").strip()
            if r.returncode == 0:
                return "Update applied, sir: " + (out.splitlines()[-1] if out else "done") + ". Restart me to load it."
            return "The update didn't apply cleanly, sir: " + (out[:160] if out else "unknown error")
        except Exception as e:
            return f"I couldn't apply the update, sir ({e})."

    # ---- self-review ----
    def improvement_plan(self) -> str:
        from core import eval_harness
        res = eval_harness.run()
        fails = [r["name"] for r in res["results"] if not r["ok"]]
        base = (f"Current reliability is {res['score']}%. " +
                ("Failing checks: " + ", ".join(fails) + ". " if fails else "All self-checks pass. "))
        llm = self.orch.llm
        if llm and getattr(llm, "available", False):
            ans = llm.chat(self.orch.system_prompt,
                "You are JARVIS reviewing your own system honestly. Given this status, propose the top 3 "
                "concrete, safe improvements to make next — each one line, specific and realistic, no fluff. "
                "Status: " + base + "Known future levers: real-time speech-to-speech voice, smart-home "
                "bridge, neural vector memory, longer-horizon planning.")
            if ans:
                return "Self-review, sir.\n" + base + "\n" + ans
        tips = ["Wire real-time speech-to-speech voice for a natural conversation.",
                "Add a smart-home bridge (Home Assistant) for physical-world control.",
                "Upgrade recall to neural vector memory for sharper experience reuse."]
        picks = fails[:3] if fails else tips
        return "Self-review, sir.\n" + base + "\nSuggested next steps:\n" + "\n".join("  - " + t for t in picks)
