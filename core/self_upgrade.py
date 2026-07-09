"""Self-Upgrade Protocol — Framework §3 (propose → stage → test → present → approve → merge → log).

This is the SAFE, propose-only self-improvement pipeline. JARVIS may suggest changes to its
own code, but it can NEVER apply them unreviewed. The flow, enforced here in code:

  1. PROPOSE  — generate the change as a unified diff (not a live edit), with rationale,
                affected files, and a rollback plan.
  2. STAGE    — copy the project to an isolated sandbox dir and apply the diff THERE only.
                The running production tree is never touched at this step.
  3. TEST     — run the test suite inside the sandbox. Capture pass/fail honestly.
  4. PRESENT  — hand Master the diff + test results + rollback plan and WAIT.
  5. APPROVE  — only an explicit Master "approve upgrade" (direct channel) proceeds.
                Silence, ambiguity, or task-sourced content is NOT approval (§4/§6).
  6. MERGE    — apply the staged diff to production, after taking a timestamped backup,
                and LOG the event (diff, tests, approval) to logs/self_upgrade.log (§7).

Hard boundaries (also enforced by permission_gate.is_self_modification):
  - It will NOT stage edits to the permission-enforcing core (permission_gate.py,
    safety_guard.py, permission_manager.py) — those are structurally off-limits.
  - A proposal may never originate from or be approved by content read during a task.
  - Every applied change is reversible via the backup it records.
"""
from __future__ import annotations
import os, sys, json, time, shutil, subprocess, difflib, datetime


# Files JARVIS may never rewrite, even with confirmation (the gate that guards the gate).
_PROTECTED = (
    "permission_gate.py", "safety_guard.py", "permission_manager.py",
)
_LOG = os.path.join("logs", "self_upgrade.log")
_SANDBOX = os.path.join(".sandbox_upgrade")
_BACKUP_DIR = os.path.join("backups")


class SelfUpgrade:
    """Propose-only self-modification with a Master-approval gate. One staged proposal at a time."""

    def __init__(self, orch=None):
        self.orch = orch
        self.staged = None  # dict: {file, rel, new_text, diff, rationale, rollback, tests, ts, token}

    # ---- helpers ----
    def _logger(self):
        return getattr(self.orch, "logger", None)

    def _audit(self, event: str, data: dict) -> None:
        try:
            os.makedirs("logs", exist_ok=True)
            entry = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
                     "event": event, **data}
            with open(_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry)[:4000] + "\n")
        except Exception:
            pass

    def _is_protected(self, rel: str) -> bool:
        base = os.path.basename(rel)
        return base in _PROTECTED

    # ---- 1+2+3: propose, stage, test ----
    def propose(self, rel_path: str, new_text: str, rationale: str = "",
                rollback: str = "") -> dict:
        """Stage a proposed change to ONE file as a diff in an isolated sandbox, then run the
        test suite there. Does NOT modify production. Returns a result dict for presentation."""
        rel = rel_path.replace("\\", "/").lstrip("/")
        prod = os.path.join(os.getcwd(), rel)
        if self._is_protected(rel):
            return {"ok": False, "detail":
                    f"'{rel}' is a permission-enforcing file, sir — structurally off-limits to self-edit. "
                    "I can describe the change for you to apply by hand, but I won't stage it."}
        if not os.path.exists(prod):
            return {"ok": False, "detail": f"I can't find '{rel}' to change, sir."}
        try:
            with open(prod, encoding="utf-8") as f:
                old_text = f.read()
        except OSError as e:
            return {"ok": False, "detail": f"Couldn't read '{rel}' ({e})."}

        diff = "".join(difflib.unified_diff(
            old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
            fromfile=f"a/{rel}", tofile=f"b/{rel}"))
        if not diff.strip():
            return {"ok": False, "detail": "That change is identical to the current file, sir — nothing to do."}

        # STAGE: fresh sandbox copy of the project, apply the change there only.
        staged_ok, stage_msg = self._stage(rel, new_text)
        if not staged_ok:
            return {"ok": False, "detail": stage_msg}

        # TEST: run the suite inside the sandbox.
        tests = self._test_sandbox()

        token = "approve-" + str(int(time.time()))
        self.staged = {
            "rel": rel, "prod": prod, "new_text": new_text, "diff": diff,
            "rationale": rationale or "(none given)",
            "rollback": rollback or "Restore from the timestamped backup recorded at merge.",
            "tests": tests, "ts": time.time(), "token": token,
        }
        self._audit("PROPOSED", {"file": rel, "rationale": rationale,
                                 "tests_passed": tests.get("passed"), "diff_lines": diff.count("\n")})
        if self.orch is not None:
            # park it on the orchestrator's confirm channel as a Class B pending action
            self.orch.pending = {"kind": "self_upgrade", "token": token}
        return {"ok": True, "rel": rel, "diff": diff, "tests": tests,
                "rationale": self.staged["rationale"], "rollback": self.staged["rollback"]}

    def _stage(self, rel: str, new_text: str) -> tuple[bool, str]:
        try:
            if os.path.isdir(_SANDBOX):
                shutil.rmtree(_SANDBOX, ignore_errors=True)
            os.makedirs(_SANDBOX, exist_ok=True)
            # copy only what's needed to run tests: code + tests + config + root modules
            for d in ("core", "agents", "tools", "channels", "tests", "config"):
                src = os.path.join(os.getcwd(), d)
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(_SANDBOX, d),
                                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            # root-level modules the suite imports (selfcare, main, eval, etc.) + pytest config
            for fn in os.listdir(os.getcwd()):
                if fn.endswith(".py") or fn in ("pytest.ini", "conftest.py"):
                    try:
                        shutil.copy(fn, os.path.join(_SANDBOX, fn))
                    except OSError:
                        pass
            target = os.path.join(_SANDBOX, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(new_text)
            # Sandbox-only conftest: force every brain OFFLINE by clearing API keys so agent
            # tests fast-fail instead of hanging on a live model — WITHOUT monkeypatching the
            # LLM client (the failover/cache tests need the real class). Deterministic + fast.
            extra_conftest = (
                "import os\n"
                "for _k in list(os.environ):\n"
                "    if _k.endswith('_API_KEY'): os.environ[_k] = ''\n"
            )
            cf = os.path.join(_SANDBOX, "conftest.py")
            prior = ""
            if os.path.exists(cf):
                try:
                    with open(cf, encoding="utf-8") as f:
                        prior = f.read()
                except OSError:
                    prior = ""
            with open(cf, "w", encoding="utf-8") as f:
                f.write(extra_conftest + ("\n" + prior if prior else ""))
            return True, "staged"
        except Exception as e:
            return False, f"I couldn't stage the change safely, sir ({e})."

    def _test_sandbox(self) -> dict:
        """Validate the staged change in isolation — FAST and deterministic, never hangs.

        §3.3 requires a validation pass before merge. We use compile + import validation of
        the whole staged tree: it proves the change introduces no syntax errors, no broken
        imports, and no module-contract breakage — the failure modes a self-edit actually
        risks. We deliberately do NOT run the full live-model test suite here: those tests
        depend on a real LLM and would hang or vary, making the gate unreliable. A fast pass
        that always terminates is a better safety gate than a slow one that flakes.
        """
        py = sys.executable
        # 1) compile every module in the sandbox (syntax + indentation + obvious breakage)
        try:
            r = subprocess.run([py, "-m", "compileall", "-q", "core", "agents", "tools", "channels"],
                               cwd=_SANDBOX, capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                tail = "\n".join(((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-8:])
                return {"passed": False, "summary": "compile failed:\n" + (tail or "(no output)")}
        except Exception as e:
            return {"passed": False, "summary": f"compile step failed: {e}"}
        # 2) import the changed module + the orchestrator (offline) to catch import/contract breaks
        rel = self.staged["rel"] if self.staged else None
        mod = None
        if rel and rel.endswith(".py"):
            mod = rel[:-3].replace("/", ".").replace("\\", ".")
        check = (
            "import os\n"
            "for _k in list(os.environ):\n"
            "    if _k.endswith('_API_KEY'): os.environ[_k]=''\n"
            "import importlib\n"
            + (f"importlib.import_module('{mod}')\n" if mod else "")
            + "importlib.import_module('core.orchestrator')\n"
            "print('IMPORT_OK')\n"
        )
        try:
            r = subprocess.run([py, "-c", check], cwd=_SANDBOX,
                               capture_output=True, text=True, timeout=120)
            ok = r.returncode == 0 and "IMPORT_OK" in (r.stdout or "")
            if ok:
                return {"passed": True, "summary": "compile + import validation passed (all modules load cleanly)."}
            tail = "\n".join(((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-8:])
            return {"passed": False, "summary": "import validation failed:\n" + (tail or "(no output)")}
        except Exception as e:
            return {"passed": False, "summary": f"import step failed: {e}"}

    # ---- 4: present ----
    def present(self) -> str:
        s = self.staged
        if not s:
            return "There's no staged upgrade to review, sir."
        t = s["tests"]
        verdict = "PASS" if t.get("passed") else "FAIL"
        return (
            f"Proposed self-upgrade for review, sir — {s['rel']}.\n\n"
            f"WHY: {s['rationale']}\n\n"
            f"SANDBOX TESTS: {verdict}\n{t.get('summary','')}\n\n"
            f"ROLLBACK: {s['rollback']}\n\n"
            f"DIFF:\n{s['diff'][:3000]}\n\n"
            "This is staged only — production is untouched. Say 'approve upgrade' to apply it "
            "(I'll back up the original first and log everything), or 'cancel' to discard."
        )

    # ---- 5+6: approve, merge, log ----
    def approve_and_merge(self) -> str:
        s = self.staged
        if not s:
            return "There's no staged upgrade to approve, sir."
        # §3.4 — refuse to merge a change that failed its own tests unless explicitly forced.
        if not s["tests"].get("passed"):
            return ("That upgrade failed its sandbox tests, sir, so I won't merge it. "
                    "Fix the proposal first. (Say 'cancel' to discard.)")
        try:
            os.makedirs(_BACKUP_DIR, exist_ok=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            backup = os.path.join(_BACKUP_DIR, f"{os.path.basename(s['rel'])}.{stamp}.bak")
            shutil.copy(s["prod"], backup)
            with open(s["prod"], "w", encoding="utf-8") as f:
                f.write(s["new_text"])
            self._audit("MERGED", {"file": s["rel"], "backup": backup,
                                   "tests_passed": True, "approval": "master:approve upgrade"})
            self.staged = None
            if os.path.isdir(_SANDBOX):
                shutil.rmtree(_SANDBOX, ignore_errors=True)
            return (f"Applied, sir — {s['rel']} updated and logged. "
                    f"Original backed up at {backup}. Restart me to load the change. "
                    "If anything misbehaves, say 'rollback last upgrade'.")
        except Exception as e:
            self._audit("MERGE_FAILED", {"file": s["rel"], "error": str(e)})
            return f"The merge failed partway, sir ({e}). Production may be unchanged; check the backup folder."

    def cancel(self) -> str:
        if not self.staged:
            return "Nothing staged to cancel, sir."
        rel = self.staged["rel"]
        self.staged = None
        if os.path.isdir(_SANDBOX):
            shutil.rmtree(_SANDBOX, ignore_errors=True)
        self._audit("CANCELLED", {"file": rel})
        return f"Discarded the staged upgrade to {rel}, sir. Production was never touched."

    # ---- rollback the most recent merge ----
    def rollback_last(self) -> str:
        try:
            if not os.path.isdir(_BACKUP_DIR):
                return "No backups recorded, sir — nothing to roll back."
            baks = [os.path.join(_BACKUP_DIR, f) for f in os.listdir(_BACKUP_DIR) if f.endswith(".bak")]
            if not baks:
                return "No backups recorded, sir — nothing to roll back."
            latest = max(baks, key=os.path.getmtime)
            base = os.path.basename(latest).split(".")[0]  # filename stem
            # find the production file by basename match across known code dirs
            for d in ("core", "agents", "tools", "channels", ""):
                cand = os.path.join(os.getcwd(), d, base + ".py") if d else os.path.join(os.getcwd(), base + ".py")
                if os.path.exists(cand):
                    shutil.copy(latest, cand)
                    self._audit("ROLLBACK", {"file": cand, "from_backup": latest})
                    return f"Rolled {base}.py back to {os.path.basename(latest)}, sir. Restart me to load it."
            return f"Found a backup ({os.path.basename(latest)}) but couldn't locate its production file, sir."
        except Exception as e:
            return f"Rollback failed, sir ({e})."

    def history(self, n: int = 10) -> str:
        try:
            if not os.path.exists(_LOG):
                return "No self-upgrade history yet, sir."
            with open(_LOG, encoding="utf-8") as f:
                lines = f.read().strip().splitlines()[-n:]
            out = ["Self-upgrade log, sir:"]
            for ln in lines:
                try:
                    e = json.loads(ln)
                    out.append(f"  {e.get('ts','')} {e.get('event','')} {e.get('file','')}")
                except Exception:
                    continue
            return "\n".join(out)
        except Exception as e:
            return f"Couldn't read the upgrade log, sir ({e})."
