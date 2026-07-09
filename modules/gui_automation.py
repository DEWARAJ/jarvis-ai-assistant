"""JARVIS v6.0 — GUI automation via pyautogui/pygetwindow."""
from __future__ import annotations
import time

try: import pyautogui; pyautogui.FAILSAFE = True; _PAG = True
except ImportError: _PAG = False

try: import pygetwindow as gw; _GW = True
except ImportError: _GW = False


def take_screenshot_and_analyze(prompt: str = "Describe what you see") -> str:
    if not _PAG: return "pyautogui not installed."
    try:
        from modules.display_control import take_screenshot
        import os, anthropic, base64
        path = take_screenshot()
        key = os.getenv("ANTHROPIC_API_KEY","")
        if not key: return f"Screenshot: {path}. No API key for vision."
        with open(path, "rb") as f:
            b64 = base64.standard_b64encode(f.read()).decode()
        client = anthropic.Anthropic(api_key=key)
        r = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1024,
            messages=[{"role":"user","content":[
                {"type":"image","source":{"type":"base64","media_type":"image/png","data":b64}},
                {"type":"text","text":prompt}]}])
        return r.content[0].text
    except Exception as e: return f"Vision error: {e}"


def get_open_windows() -> list[str]:
    if not _GW: return ["pygetwindow not installed"]
    try: return [w.title for w in gw.getAllWindows() if w.title.strip()]
    except Exception as e: return [f"Error: {e}"]


def focus_window(title: str) -> str:
    if not _GW: return "pygetwindow not installed."
    try:
        wins = gw.getWindowsWithTitle(title)
        if not wins: return f"No window '{title}'"
        wins[0].activate(); time.sleep(0.3)
        return f"Focused: {wins[0].title}"
    except Exception as e: return f"Focus error: {e}"


def close_window(title: str, confirmed: bool = False) -> str:
    if not _GW: return "pygetwindow not installed."
    try:
        wins = gw.getWindowsWithTitle(title)
        if not wins: return f"No window '{title}'"
        wins[0].close(); return f"Closed: {title}"
    except Exception as e: return f"Close error: {e}"


def click_at(x: int, y: int, button: str = "left",
             confirmed: bool = False) -> str:
    if not _PAG: return "pyautogui not installed."
    try:
        pyautogui.click(x, y, button=button)
        return f"Clicked {button} at ({x},{y})"
    except Exception as e: return f"Click error: {e}"


def type_text(text: str, interval: float = 0.05, confirmed: bool = False) -> str:
    if not _PAG: return "pyautogui not installed."
    try:
        pyautogui.typewrite(text, interval=interval)
        return f"Typed: {text[:40]}"
    except Exception as e: return f"Type error: {e}"


def press_hotkey(*keys: str, confirmed: bool = False) -> str:
    if not _PAG: return "pyautogui not installed."
    try:
        pyautogui.hotkey(*keys)
        return f"Pressed: {'+'.join(keys)}"
    except Exception as e: return f"Hotkey error: {e}"
