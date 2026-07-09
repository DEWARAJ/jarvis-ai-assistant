"""Close / kill / verify Windows processes via psutil + taskkill. Verifiable, no admin (own apps)."""
from __future__ import annotations
import sys, subprocess, time
from tools.base_tool import BaseTool

# friendly name -> process exe
PROCS = {
    "notepad": "notepad.exe", "calculator": "CalculatorApp.exe", "calc": "CalculatorApp.exe",
    "chrome": "chrome.exe", "edge": "msedge.exe", "firefox": "firefox.exe",
    "word": "WINWORD.EXE", "excel": "EXCEL.EXE", "powerpoint": "POWERPNT.EXE",
    "spotify": "Spotify.exe", "vlc": "vlc.exe", "code": "Code.exe", "vscode": "Code.exe",
    "paint": "mspaint.exe", "explorer": "explorer.exe", "discord": "Discord.exe",
    "task manager": "Taskmgr.exe", "taskmgr": "Taskmgr.exe", "wordpad": "wordpad.exe",
}


class ProcessControlTool(BaseTool):
    name = "process"; scope = "close / kill apps"

    def _exe(self, name: str) -> str:
        low = (name or "").strip().lower()
        if low in PROCS:
            return PROCS[low]
        return low if low.endswith(".exe") else low + ".exe"

    def _running(self, exe: str) -> bool:
        try:
            import psutil
            for p in psutil.process_iter(["name"]):
                if (p.info.get("name") or "").lower() == exe.lower():
                    return True
            return False
        except ImportError:
            # fall back to tasklist
            try:
                out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe}"],
                                     capture_output=True, text=True, timeout=10).stdout.lower()
                return exe.lower() in out
            except Exception:
                return False

    def close(self, name: str, force: bool = False) -> dict:
        exe = self._exe(name)
        disp = name.strip().title()
        if not sys.platform.startswith("win"):
            return {"action": "close", "started": True, "verified": True,
                    "spoken": f"(Would close {disp} on Windows.)", "debug": f"simulated {exe}"}
        if not self._running(exe):
            return {"action": "close", "started": False, "verified": False,
                    "spoken": f"I couldn't find {disp} running.", "debug": f"{exe} not running"}
        # graceful, then force
        try:
            subprocess.run(["taskkill", "/IM", exe], capture_output=True, text=True, timeout=10)
            time.sleep(0.8)
            if self._running(exe):
                subprocess.run(["taskkill", "/IM", exe, "/F"], capture_output=True, text=True, timeout=10)
                time.sleep(0.8)
        except Exception as e:
            return {"action": "close", "started": True, "verified": False,
                    "spoken": f"I tried to close {disp} but hit an error ({e}).", "debug": str(e)}
        gone = not self._running(exe)
        return {"action": "close", "started": True, "verified": gone,
                "spoken": f"{disp} is closed." if gone else
                          f"I sent the close command but {disp} is still running — it may need admin.",
                "debug": f"{exe} gone={gone}"}

    def kill(self, name: str) -> dict:
        return self.close(name, force=True)
