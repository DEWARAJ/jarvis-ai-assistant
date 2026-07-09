"""System capability check — tells JARVIS (and you) exactly what works on this machine."""
from __future__ import annotations
import sys, platform


def _have(mod: str) -> bool:
    try:
        __import__(mod); return True
    except Exception:
        return False


def is_admin() -> bool:
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def report() -> str:
    win = sys.platform.startswith("win")
    psutil = _have("psutil")
    pg = _have("pyautogui")
    pcaw = _have("pycaw")
    pw = _have("playwright")
    admin = is_admin()

    def line(label, ok, note=""):
        mark = "working" if ok else "needs setup"
        return f"  {label}: {mark}{(' — ' + note) if note else ''}"

    lines = [
        "System check:",
        f"  OS: {platform.system()} {platform.release()}  ·  Python {platform.python_version()}",
        f"  Administrator: {'yes' if admin else 'no (some Wi-Fi actions need this)'}",
        line("App open/launch", win, "" if win else "Windows only"),
        line("Browser & search (open sites, Google/YouTube)", True),
        line("YouTube search", True),
        line("YouTube auto-play first result", pw, "install playwright for auto-click; else opens results"),
        line("Close / kill apps", win and (psutil or True), "uses taskkill" + ("" if psutil else "; psutil recommended")),
        line("Process verification", psutil, "" if psutil else "install psutil to confirm a process closed"),
        line("Volume control", pg, "" if pg else "install pyautogui"),
        line("Keyboard / mouse / type", pg, "" if pg else "install pyautogui"),
        line("Screenshots", _have("PIL"), "" if _have("PIL") else "install pillow"),
        line("Wi-Fi toggle", win, "needs administrator; otherwise opens settings"),
        line("Bluetooth toggle", False, "Windows blocks app toggling; opens settings"),
        line("App-launch verification", psutil, "" if psutil else "install psutil"),
    ]
    if not (psutil and pg):
        lines.append("  To unlock everything: pip install psutil pyautogui pillow")
    return "\n".join(lines)
