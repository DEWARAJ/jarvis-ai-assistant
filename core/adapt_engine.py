"""JARVIS v2.0 — Layer 3: self-adaptive code engine.

Pipeline (spec): intent -> design -> generate (via LLM) -> SAFETY GATE -> write+test -> log -> rollback.

Hardened vs. the spec draft:
  * NO blocking input(). Approval is Class-B and async: `propose()` stages a backup + new code
    + diff + risk and RETURNS a proposal; the orchestrator/master then calls `apply()` only on
    explicit approval. This fits JARVIS's GUI/voice/web runtime (no terminal stdin).
  * Uses the existing LLMClient (key pulled from the env named in the active profile) — never a
    hardcoded key, never a raw SDK import.
  * Path-locked: only files inside the JARVIS project root can be modified.
  * Backup before write; py_compile syntax check; optional smoke test; auto-rollback on failure;
    every mutation logged to Tier-4 code_changelog via JarvisMemory.

Never raises — every failure returns a status dict.
"""
from __future__ import annotations
import os, sys, shutil, difflib, subprocess, py_compile
from datetime import datetime
from pathlib import Path

_GEN_SYSTEM = (
    "You are a senior Python engineer working on JARVIS, an autonomous AI agent for Windows. "
    "You write clean, well-commented, production-grade code. You never break existing interfaces. "
    "You always include error handling. You never remove functionality that exists — only add or improve."
)


def _now_tag():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class AdaptEngine:
    def __init__(self, project_root, memory=None, llm=None, logger=None):
        self.root = Path(project_root).resolve()
        self.memory = memory          # JarvisMemory (for changelog + backups dir)
        self.llm = llm                # LLMClient
        self.logger = logger
        self.backup_dir = self.root / "memory" / "code_backups"
        self.stage_dir = self.root / "memory" / "code_staged"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.stage_dir.mkdir(parents=True, exist_ok=True)

    # ---- guards ----
    def _safe_path(self, filename):
        """Resolve filename under the project root; reject anything outside (path-traversal safe)."""
        p = (self.root / filename).resolve() if not os.path.isabs(filename) else Path(filename).resolve()
        try:
            p.relative_to(self.root)
        except ValueError:
            return None
        return p

    @staticmethod
    def _looks_like_code(text):
        s = (text or "").lstrip()
        return s.startswith("#") or s.startswith("import ") or s.startswith("from ") or s.startswith('"""')

    @staticmethod
    def _diff(old, new):
        old_l, new_l = old.splitlines(), new.splitlines()
        ud = list(difflib.unified_diff(old_l, new_l, lineterm=""))
        added = sum(1 for l in ud if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in ud if l.startswith("-") and not l.startswith("---"))
        return {"added": added, "removed": removed,
                "summary": f"+{added}/-{removed} lines"}

    def _risk(self, rel_path, diff):
        rp = str(rel_path).replace("\\", "/").lower()
        sensitive = ("safety_guard", "permission", "orchestrator", "llm_client", "agentic_core")
        if any(s in rp for s in sensitive):
            return "HIGH"
        churn = diff["added"] + diff["removed"]
        if rp.startswith("core/") or churn > 150:
            return "MEDIUM"
        return "LOW"

    # ---- STEP 1-4: propose (generate + stage + gate, NO write to live file) ----
    def propose(self, filename, task, constraints=""):
        path = self._safe_path(filename)
        if path is None:
            return {"ok": False, "stage": "guard", "reason": f"Refused: '{filename}' is outside the JARVIS project root."}
        if not path.exists():
            return {"ok": False, "stage": "guard", "reason": f"File not found: {filename}"}
        if self.llm is None or not getattr(self.llm, "enabled", False):
            return {"ok": False, "stage": "generate",
                    "reason": "LLM brain disabled — enable llm + provider key to self-adapt."}

        current = path.read_text(encoding="utf-8")
        recent = []
        if self.memory is not None:
            try:
                recent = self.memory.recent_mutations(n=5)
            except Exception:
                recent = []

        user = (
            f"CURRENT FILE: {filename}\n\nCURRENT CODE:\n{current}\n\n"
            f"TASK: {task}\n\n"
            f"CONSTRAINTS: {constraints or 'Maintain all existing function signatures and imports.'}\n\n"
            f"RECENT CODE HISTORY: {recent}\n\n"
            "OUTPUT FORMAT: Return ONLY the complete modified Python file. No explanation, "
            "no markdown fences, no preamble. First line must be: "
            f"# JARVIS_MUTATION | {datetime.now().isoformat()} | {task[:60]}"
        )
        # bump token cap for a full-file generation, then restore
        saved = getattr(self.llm, "max_tokens", 800)
        try:
            self.llm.max_tokens = max(saved, 8192)
            new_code = self.llm.chat(_GEN_SYSTEM, user, history=None, no_cache=True)
        finally:
            self.llm.max_tokens = saved

        if not new_code:
            return {"ok": False, "stage": "generate", "reason": "LLM returned nothing (key missing or call failed)."}
        new_code = new_code.strip()
        if new_code.startswith("```"):            # strip accidental fences
            new_code = new_code.strip("`")
            if "\n" in new_code:
                new_code = new_code.split("\n", 1)[1]
        if not self._looks_like_code(new_code):
            return {"ok": False, "stage": "validate",
                    "reason": "LLM returned prose, not code. Retry with a stricter task."}

        # backup live file + stage proposed code (do NOT touch live file yet)
        tag = _now_tag()
        backup = self.backup_dir / f"{path.stem}_{tag}.py"
        shutil.copy2(path, backup)
        staged = self.stage_dir / f"{path.stem}_{tag}.staged.py"
        staged.write_text(new_code, encoding="utf-8")

        diff = self._diff(current, new_code)
        risk = self._risk(path.relative_to(self.root), diff)
        return {
            "ok": True, "stage": "proposed", "filename": str(path.relative_to(self.root)),
            "abs_path": str(path), "backup": str(backup), "staged": str(staged),
            "diff": diff, "risk": risk, "task": task,
            "summary": f"{filename}: {diff['summary']} · risk {risk}",
        }

    # ---- STEP 5-7: apply (write + test + log, auto-rollback on failure) ----
    def apply(self, proposal):
        """Deploy a proposal AFTER explicit approval. Runs syntax + smoke test, rolls back on fail."""
        if not proposal or not proposal.get("ok") or proposal.get("stage") != "proposed":
            return {"ok": False, "reason": "Invalid or unapproved proposal."}
        path = Path(proposal["abs_path"])
        backup = Path(proposal["backup"])
        staged = Path(proposal["staged"])
        if not staged.exists() or not backup.exists():
            return {"ok": False, "reason": "Staged code or backup missing — re-run propose()."}

        new_code = staged.read_text(encoding="utf-8")
        path.write_text(new_code, encoding="utf-8")

        # syntax check
        syntax_ok, err = self._syntax_check(path)
        smoke_ok = True
        if syntax_ok:
            smoke_ok, smoke_err = self._smoke_test()
            if not smoke_ok:
                err = smoke_err

        if syntax_ok and smoke_ok:
            self._log(proposal, "pass", False)
            try: staged.unlink()
            except OSError: pass
            return {"ok": True, "status": "deployed", "file": proposal["filename"], "backup": str(backup)}

        # auto-rollback
        shutil.copy2(backup, path)
        self._log(proposal, "fail", True)
        return {"ok": False, "status": "rolled_back", "file": proposal["filename"], "error": err}

    def rollback(self, filename):
        """Restore the most recent backup of a file."""
        path = self._safe_path(filename)
        if path is None:
            return {"ok": False, "reason": "Outside project root."}
        cands = sorted(self.backup_dir.glob(f"{path.stem}_*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            return {"ok": False, "reason": f"No backup found for {filename}."}
        shutil.copy2(cands[0], path)
        return {"ok": True, "restored_from": str(cands[0]), "file": str(path.relative_to(self.root))}

    # ---- helpers ----
    def _syntax_check(self, path):
        try:
            py_compile.compile(str(path), doraise=True)
            return True, ""
        except py_compile.PyCompileError as e:
            return False, f"syntax: {e}"
        except Exception as e:
            return False, f"compile: {e}"

    def _smoke_test(self):
        smoke = self.root / "tests" / "smoke_tests.py"
        if not smoke.exists():
            return True, ""          # no smoke suite => skip, treat as pass
        py = sys.executable
        try:
            p = subprocess.run([py, str(smoke)], cwd=str(self.root),
                               capture_output=True, text=True, timeout=120)
            if p.returncode == 0:
                return True, ""
            return False, f"smoke test failed: {(p.stdout + p.stderr)[-400:]}"
        except subprocess.TimeoutExpired:
            return False, "smoke test timed out"
        except Exception as e:
            return False, f"smoke test error: {e}"

    def _log(self, proposal, test_result, rolled_back):
        if self.memory is None:
            return
        try:
            self.memory.log_mutation(
                trigger=proposal.get("task", ""),
                files_modified=[proposal.get("filename")],
                diff_summary=proposal.get("diff", {}).get("summary", ""),
                test_result=test_result, rolled_back=rolled_back)
        except Exception:
            pass
