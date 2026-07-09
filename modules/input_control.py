"""JARVIS v6.0 — Keyboard and mouse simulation via pyautogui/pynput."""
from __future__ import annotations
import time

try: import pyautogui; pyautogui.FAILSAFE = True; _PAG = True
except ImportError: _PAG = False

try: from pynput import keyboard as _kb, mouse as _ms; _PYNPUT = True
except ImportError: _PYNPUT = False


def type_text(text: str, interval: float = 0.05, confirmed: bool = False) -> str:
    if not _PAG: return "pyautogui not installed."
    try: pyautogui.typewrite(text, interval=interval); return f"Typed: {text[:40]}"
    except Exception as e: return f"Type error: {e}"


def press_keys(*keys: str, confirmed: bool = False) -> str:
    if not _PAG: return "pyautogui not installed."
    try: pyautogui.hotkey(*keys); return f"Pressed: {'+'.join(keys)}"
    except Exception as e: return f"Hotkey error: {e}"


def move_mouse(x: int, y: int) -> str:
    if not _PAG: return "pyautogui not installed."
    try: pyautogui.moveTo(x, y, duration=0.2); return f"Mouse moved to ({x},{y})"
    except Exception as e: return f"Mouse error: {e}"


def click(x: int, y: int, button: str = "left", confirmed: bool = False) -> str:
    if not _PAG: return "pyautogui not installed."
    try:
        pyautogui.click(x, y, button=button)
        return f"Clicked {button} at ({x},{y})"
    except Exception as e: return f"Click error: {e}"


def scroll(x: int, y: int, clicks: int, confirmed: bool = False) -> str:
    if not _PAG: return "pyautogui not installed."
    try: pyautogui.scroll(clicks, x=x, y=y); return f"Scrolled {clicks} at ({x},{y})"
    except Exception as e: return f"Scroll error: {e}"


def get_mouse_position() -> tuple[int, int]:
    if not _PAG: return (0, 0)
    return pyautogui.position()


def get_active_window() -> str:
    try:
        import pygetwindow as gw
        w = gw.getActiveWindow()
        return w.title if w else "No active window"
    except Exception:
        return "pygetwindow not available"
