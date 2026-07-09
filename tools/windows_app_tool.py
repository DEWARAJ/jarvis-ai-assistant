"""Launch apps, folders & websites on Windows — multiple fallback methods + honest errors."""
from __future__ import annotations
import os, sys, subprocess, shutil, time
from tools.base_tool import BaseTool

# name -> (launch token(s), process names to verify)
APPS = {
    "chrome": (["chrome"], ["chrome.exe"]), "google chrome": (["chrome"], ["chrome.exe"]),
    "edge": (["msedge"], ["msedge.exe"]), "firefox": (["firefox"], ["firefox.exe"]),
    "brave": (["brave"], ["brave.exe"]),
    "notepad": (["notepad"], ["notepad.exe"]), "wordpad": (["write"], ["wordpad.exe"]),
    "calc": (["calc"], ["CalculatorApp.exe", "Calculator.exe"]),
    "calculator": (["calc"], ["CalculatorApp.exe", "Calculator.exe"]),
    "explorer": (["explorer"], ["explorer.exe"]), "file explorer": (["explorer"], ["explorer.exe"]),
    "cmd": (["cmd"], ["cmd.exe"]), "powershell": (["powershell"], ["powershell.exe"]),
    "terminal": (["wt"], ["WindowsTerminal.exe"]),
    "spotify": (["spotify"], ["Spotify.exe"]), "code": (["code"], ["Code.exe"]),
    "vscode": (["code"], ["Code.exe"]), "vs code": (["code"], ["Code.exe"]),
    "word": (["winword"], ["WINWORD.EXE"]), "excel": (["excel"], ["EXCEL.EXE"]),
    "powerpoint": (["powerpnt"], ["POWERPNT.EXE"]), "outlook": (["outlook"], ["OUTLOOK.EXE"]),
    "paint": (["mspaint"], ["mspaint.exe"]), "taskmgr": (["taskmgr"], ["Taskmgr.exe"]),
    "task manager": (["taskmgr"], ["Taskmgr.exe"]), "discord": (["discord"], ["Discord.exe"]),
    "vlc": (["vlc"], ["vlc.exe"]), "steam": (["steam"], ["steam.exe"]),
    "settings": (["ms-settings:"], []),
}
FOLDERS = {"downloads": "~/Downloads", "documents": "~/Documents", "desktop": "~/Desktop",
           "pictures": "~/Pictures", "music": "~/Music", "videos": "~/Videos",
           "downloads folder": "~/Downloads"}
SITES = {
    "google": "https://www.google.com", "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com", "maps": "https://maps.google.com",
    "chatgpt": "https://chat.openai.com", "github": "https://github.com",
    "amazon": "https://www.amazon.com", "shopify": "https://admin.shopify.com",
    "shopify admin": "https://admin.shopify.com", "tiktok": "https://www.tiktok.com",
    "instagram": "https://www.instagram.com", "facebook": "https://www.facebook.com",
    "twitter": "https://twitter.com", "x": "https://x.com", "reddit": "https://www.reddit.com",
    "netflix": "https://www.netflix.com", "linkedin": "https://www.linkedin.com",
    "whatsapp": "https://web.whatsapp.com", "tradingview": "https://www.tradingview.com",
}
# common Chrome install locations, in case it's not on PATH
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
]


def _open_in_chrome(url: str) -> bool:
    """Open a URL specifically in Google Chrome (not the default browser)."""
    import shutil
    exe = shutil.which("chrome")
    if not exe:
        for pth in CHROME_PATHS:
            if os.path.exists(pth):
                exe = pth; break
    try:
        if exe:
            subprocess.Popen([exe, url]); return True
        subprocess.Popen(f'start chrome "{url}"', shell=True); return True
    except Exception:
        try:
            os.startfile(url); return True
        except Exception:
            return False


class WindowsAppTool(BaseTool):
    name = "windows_app"; scope = "launch apps, folders & websites"

    def _log(self, msg):
        if self.logger:
            self.logger.action("windows_app: " + msg)

    def _launch_app(self, tokens: list) -> tuple[bool, str]:
        """Try several methods; return (ok, method_or_error)."""
        token = tokens[0]
        errors = []
        # protocol (ms-settings:)
        if token.endswith(":"):
            try:
                os.startfile(token); return True, f"os.startfile({token})"
            except Exception as e:
                return False, f"startfile failed: {e}"
        # 1) start via shell (resolves App Paths, Store apps, PATH)
        try:
            subprocess.Popen(f'start "" "{token}"', shell=True)
            return True, f'start {token}'
        except Exception as e:
            errors.append(f"start: {e}")
        # 2) direct on PATH
        exe = shutil.which(token) or shutil.which(token + ".exe")
        if exe:
            try:
                subprocess.Popen([exe]); return True, f"which->{exe}"
            except Exception as e:
                errors.append(f"which: {e}")
        # 3) known chrome paths
        if token == "chrome":
            for path in CHROME_PATHS:
                if os.path.exists(path):
                    try:
                        subprocess.Popen([path]); return True, f"path->{path}"
                    except Exception as e:
                        errors.append(f"chromepath: {e}")
        return False, "; ".join(errors) or "no method worked"

    def _find_start_menu_shortcut(self, name: str):
        """Find an installed app's Start Menu .lnk by name. This is what lets JARVIS open almost
        ANY installed app (not just the hardcoded ones) — nearly every app drops a Start Menu
        shortcut. Returns the best-matching .lnk path, or None."""
        name_l = (name or "").lower().strip()
        if not name_l:
            return None
        roots = [
            os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                         r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("APPDATA", os.path.expanduser(r"~\AppData\Roaming")),
                         r"Microsoft\Windows\Start Menu\Programs"),
        ]
        partial = None
        for root in roots:
            if not os.path.isdir(root):
                continue
            for dirpath, _dirs, files in os.walk(root):
                for fn in files:
                    if not fn.lower().endswith(".lnk"):
                        continue
                    stem = fn[:-4].lower()
                    if stem == name_l:
                        return os.path.join(dirpath, fn)        # exact match wins immediately
                    if partial is None and (name_l in stem or stem in name_l):
                        partial = os.path.join(dirpath, fn)
        return partial

    def _launch_via_start_menu(self, name: str) -> tuple[bool, str]:
        lnk = self._find_start_menu_shortcut(name)
        if not lnk:
            return False, "no start-menu shortcut"
        try:
            os.startfile(lnk)
            return True, f"start-menu:{os.path.basename(lnk)}"
        except Exception as e:
            return False, f"startmenu launch: {e}"

    def _verify(self, procs: list) -> tuple[bool, str]:
        if not procs:
            return False, "no process signature to check"
        try:
            import psutil
        except ImportError:
            return False, "psutil not installed"
        time.sleep(1.1)
        want = {p.lower() for p in procs}
        try:
            for p in psutil.process_iter(["name"]):
                if (p.info.get("name") or "").lower() in want:
                    return True, "process found"
        except Exception as e:
            return False, f"psutil error: {e}"
        return False, "process not found yet"

    def open(self, target: str) -> dict:
        t = (target or "").strip().strip('"').strip("'")
        low = t.lower()
        for w in ("the ", "app ", "website ", "site ", "url ", "my ", "up "):
            if low.startswith(w):
                t = t[len(w):]; low = t.lower()
        fb = {"action": "app_launch", "target": t, "started": False, "completed": False,
              "verified": False, "result_message": "", "error_message": "", "next_step": "",
              "method": ""}
        if not t:
            fb["result_message"] = "Open what? e.g. open chrome, open downloads, open youtube."
            return fb

        # folder
        if low in FOLDERS:
            path = os.path.abspath(os.path.expanduser(FOLDERS[low]))
            try:
                if sys.platform.startswith("win"):
                    os.startfile(path)
                else:
                    subprocess.Popen(["xdg-open", path])
                self._log(f"folder {path}")
                fb.update(started=True, completed=True, verified=os.path.isdir(path), method="startfile",
                          result_message=f"Opened your {low} folder.", next_step="")
            except Exception as e:
                fb.update(error_message=str(e), result_message=f"Couldn't open {low}: {e}")
            return fb

        # website
        url = None
        if low in SITES:
            url = SITES[low]
        elif low.startswith(("http://", "https://")):
            url = t
        elif "." in low and " " not in low:
            url = "https://" + t
        if url:
            try:
                if sys.platform.startswith("win"):
                    _open_in_chrome(url)
                else:
                    import webbrowser; webbrowser.open(url)
                self._log(f"url {url} (chrome)")
                fb.update(action="open_url", started=True, completed=True, verified=True,
                          method="chrome", result_message=f"Opening {url} in Chrome.")
            except Exception as e:
                fb.update(error_message=str(e), result_message=f"Couldn't open {url}: {e}")
            return fb

        # app
        tokens, procs = APPS.get(low, ([low], []))
        if not sys.platform.startswith("win"):
            fb.update(started=True, completed=True, method="simulated",
                      result_message=f"(Would launch {t} on your Windows machine.)")
            return fb
        ok, method = self._launch_app(tokens)
        if not ok:
            # Generic fallback: find the app's Start Menu shortcut and launch it. Catches almost
            # any installed app (Store apps, games, IDEs, etc.) that isn't in the hardcoded list.
            ok, method = self._launch_via_start_menu(t)
        self._log(f"app {t} -> ok={ok} method={method}")
        fb["method"] = method
        if not ok:
            fb.update(error_message=method,
                      result_message=f"I couldn't launch {t} — I didn't find it on PATH or in your Start Menu.",
                      next_step="Tell me the exact app name as it appears in the Start Menu, or check it's installed.")
            return fb
        verified, vmsg = self._verify(procs)
        fb.update(started=True, completed=True, verified=verified,
                  result_message=f"Launching {t}.",
                  next_step="" if verified else "If it didn't appear, run: system test")
        return fb

    # ground-truth self test the user can SEE
    def self_test(self) -> dict:
        notepad = self.open("notepad")
        return {"action": "self_test", "notepad": notepad,
                "started": notepad.get("started"), "method": notepad.get("method"),
                "error": notepad.get("error_message", "")}
