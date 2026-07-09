"""Windows power control for JARVIS — sleep, lock, shutdown, restart.

Safe by tier: sleep + lock run immediately; shutdown + restart require the
orchestrator's confirmation flow. Structured feedback; graceful on non-Windows.
"""
from __future__ import annotations
import sys, subprocess
from tools.base_tool import BaseTool


class PowerControlTool(BaseTool):
    name = "power"; scope = "sleep / lock / shutdown / restart"

    def _run(self, args: list) -> tuple[bool, str]:
        if not sys.platform.startswith("win"):
            return (False, "non-Windows (simulated)")
        try:
            subprocess.Popen(args, shell=False)
            return (True, "command issued")
        except Exception as e:
            return (False, str(e))

    def lock(self) -> dict:
        ok, info = self._run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return {"action": "lock", "started": ok, "spoken": "Locking your screen." if ok
                else "I couldn't lock the screen.", "debug": info}

    def sleep(self) -> dict:
        # SetSuspendState 0,1,0 -> sleep (1st arg 1 would be hibernate)
        ok, info = self._run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return {"action": "sleep", "started": ok, "spoken": "Putting the system to sleep." if ok
                else "I couldn't put it to sleep.", "debug": info}

    def shutdown(self, when: int = 0) -> dict:
        ok, info = self._run(["shutdown", "/s", "/t", str(when)])
        return {"action": "shutdown", "started": ok, "spoken": "Shutting down now." if ok
                else "I couldn't start the shutdown.", "debug": info,
                "cancel_hint": "Run 'shutdown /a' to abort." if ok else ""}

    def restart(self, when: int = 0) -> dict:
        ok, info = self._run(["shutdown", "/r", "/t", str(when)])
        return {"action": "restart", "started": ok, "spoken": "Restarting now." if ok
                else "I couldn't start the restart.", "debug": info,
                "cancel_hint": "Run 'shutdown /a' to abort." if ok else ""}
