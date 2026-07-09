"""Run shell commands (the terminal). Owner mode runs freely; only a small denylist of
catastrophic, irreversible commands is refused. Returns real stdout/stderr — never fakes it."""
from __future__ import annotations
import subprocess, sys
from tools.base_tool import BaseTool

# irreversible / destructive patterns we refuse outright (even in owner mode)
DENY = ("format ", "format c", "del /s", "del /q", "rmdir /s", "rd /s", "rd /q",
        "diskpart", "mkfs", "rm -rf /", "rm -rf ~", ":(){", "cipher /w", "bcdedit",
        "reg delete hklm", "vssadmin delete", "wmic shadowcopy delete", "fsutil ")


class SystemCommandTool(BaseTool):
    name = "terminal"; scope = "run shell commands"

    def run(self, command: str) -> dict:
        cmd = (command or "").strip()
        if not cmd:
            return {"ok": False, "spoken": "What command shall I run, sir?", "debug": ""}
        low = cmd.lower()
        if any(p in low for p in DENY):
            return {"ok": False,
                    "spoken": "I won't run that one, sir — it's irreversible and would risk your system. "
                              "Anything short of that, I'll run gladly.",
                    "debug": "denied: catastrophic pattern"}
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=45)
            out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
            out = out.strip()
            short = out[:1500] + (" …" if len(out) > 1500 else "")
            if r.returncode == 0:
                spoken = f"Done, sir." + (f"\n{short}" if short else "")
            else:
                spoken = f"It ran but exited with code {r.returncode}, sir." + (f"\n{short}" if short else "")
            return {"ok": r.returncode == 0, "spoken": spoken, "debug": f"rc={r.returncode}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "spoken": "That command took too long and I stopped it, sir.", "debug": "timeout"}
        except Exception as e:
            return {"ok": False, "spoken": f"I couldn't run that, sir ({e}).", "debug": str(e)}
