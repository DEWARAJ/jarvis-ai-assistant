"""JARVIS v6.0 — Self-adaptation pipeline: propose -> approve -> backup -> write -> test -> rollback."""
from __future__ import annotations
import os, json, shutil, subprocess
from datetime import datetime
from pathlib import Path

_BACKUPS_DIR = Path("memory") / "code_backups"
_BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
_CHANGELOG = Path("memory") / "code_changelog.jsonl"

_ADAPT_SYSTEM = """\
You are JARVIS's self-improvement engine. Given a code file and improvement goal,
produce the COMPLETE improved file content. Do NOT use diff format. Return ONLY
the full Python code -- no explanation, no markdown fence."""


def propose_change(file_path: str, goal: str) -> str:
    """Generate improved version of file using Claude. Returns proposed new content."""
    key = os.getenv("ANTHROPIC_API_KEY","")
    if not key: return "[Error] ANTHROPIC_API_KEY not set."
    p = Path(file_path)
    if not p.exists(): return f"[Error] File not found: {file_path}"
    current = p.read_text(encoding="utf-8")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        prompt = f"File: {file_path}\n\nGoal: {goal}\n\nCurrent content:\n```python\n{current}\n```\n\nImproved version:"
        r = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=8000,
            system=_ADAPT_SYSTEM,
            messages=[{"role":"user","content":prompt}])
        proposed = r.content[0].text.strip()
        # Strip markdown fences if present
        if proposed.startswith("```"):
            lines = proposed.split("\n")
            proposed = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        return proposed
    except Exception as e: return f"[Error] Propose failed: {e}"


def backup_file(file_path: str, reason: str = "") -> str:
    """Backup file to memory/code_backups/. Returns backup path."""
    p = Path(file_path)
    if not p.exists(): return f"[Error] {file_path} not found."
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{p.stem}_{ts}{p.suffix}"
    dest = _BACKUPS_DIR / backup_name
    shutil.copy2(p, dest)
    entry = {"ts": datetime.now().isoformat(timespec="seconds"),
             "file": str(file_path), "backup_path": str(dest), "reason": reason}
    with open(_CHANGELOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return str(dest)


def apply_change(file_path: str, new_content: str,
                 confirmed: bool = False) -> str:
    """Class B: apply new content to file. Backs up first."""
    if not confirmed:
        return (f"Class B: modify '{file_path}' requires confirmation.\n"
                f"Preview (first 200 chars):\n{new_content[:200]}...")
    backup_path = backup_file(file_path, reason="pre-adapt backup")
    p = Path(file_path)
    tmp = p.with_suffix(".tmp_jarvis")
    try:
        tmp.write_text(new_content, encoding="utf-8")
        os.replace(tmp, p)
        return f"Applied to {file_path}. Backup: {backup_path}"
    except Exception as e:
        if tmp.exists(): tmp.unlink()
        return f"[Error] Apply failed: {e}"
    finally:
        if tmp.exists():
            try: tmp.unlink()
            except: pass


def smoke_test(file_path: str) -> tuple[bool, str]:
    """Quick import test for Python files. Returns (passed, output)."""
    p = Path(file_path)
    if not p.exists(): return False, f"{file_path} not found."
    if p.suffix != ".py": return True, "Non-Python file, skip test."
    result = subprocess.run(
        ["python", "-c", f"import importlib.util; "
         f"spec=importlib.util.spec_from_file_location('m',r'{p}'); "
         f"mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); "
         f"print('OK')"],
        capture_output=True, text=True, timeout=15)
    passed = result.returncode == 0
    out = result.stdout.strip() or result.stderr.strip()
    return passed, out


def rollback(file_path: str, backup_path: str | None = None,
             confirmed: bool = False) -> str:
    """Class C: roll back file to backup. Requires double confirmation."""
    if not confirmed:
        return (f"Class C: rollback '{file_path}' requires double confirmation. "
                f"This will OVERWRITE the current file.")
    if backup_path is None:
        # Find most recent backup
        stem = Path(file_path).stem
        backups = sorted(_BACKUPS_DIR.glob(f"{stem}_*.py"), reverse=True)
        if not backups: return f"No backups found for {file_path}."
        backup_path = str(backups[0])
    shutil.copy2(backup_path, file_path)
    entry = {"ts": datetime.now().isoformat(timespec="seconds"),
             "file": str(file_path), "backup_path": str(backup_path),
             "reason": "rollback"}
    with open(_CHANGELOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return f"Rolled back {file_path} from {backup_path}"


def adapt_file(file_path: str, goal: str, confirmed: bool = False) -> str:
    """Full adapt pipeline: propose -> confirm -> backup -> apply -> test -> rollback on fail."""
    proposed = propose_change(file_path, goal)
    if proposed.startswith("[Error]"): return proposed
    if not confirmed:
        return (f"Proposed change for {file_path}:\nGoal: {goal}\n"
                f"Preview:\n{proposed[:300]}...\n\n"
                f"Confirm to apply (Class B).")
    backup_path = backup_file(file_path, reason=f"pre-adapt: {goal}")
    result = apply_change(file_path, proposed, confirmed=True)
    passed, test_out = smoke_test(file_path)
    if not passed:
        rollback(file_path, backup_path, confirmed=True)
        return (f"Adapt FAILED smoke test. Rolled back.\n"
                f"Test output: {test_out}")
    return f"Adapt SUCCESS: {result}\nTest: {test_out}"


def list_backups(file_path: str | None = None) -> list[dict]:
    if not _CHANGELOG.exists(): return []
    out = []
    with open(_CHANGELOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            entry = json.loads(line)
            if file_path is None or file_path in entry.get("file",""):
                out.append(entry)
    return out[-20:]
