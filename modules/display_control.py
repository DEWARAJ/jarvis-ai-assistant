"""JARVIS v6.0 — Display control: brightness, resolution, screenshots."""
from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path

try: import screen_brightness_control as sbc; _SBC = True
except ImportError: _SBC = False

try: from PIL import ImageGrab; _PIL = True
except ImportError: _PIL = False


def get_brightness() -> int | str:
    if not _SBC: return "screen-brightness-control not installed."
    try: b = sbc.get_brightness(); return b[0] if isinstance(b, list) else b
    except Exception as e: return f"Error: {e}"


def set_brightness(level: int, confirmed: bool = False) -> str:
    if not _SBC: return "screen-brightness-control not installed."
    level = max(0, min(100, level))
    try: sbc.set_brightness(level); return f"Brightness set to {level}%."
    except Exception as e: return f"Brightness error: {e} (may need admin rights)"


def take_screenshot(region: tuple | None = None, save_dir: str = "screenshots") -> str:
    if not _PIL: return "Pillow not installed."
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = str(Path(save_dir) / f"screenshot_{ts}.png")
    try:
        img = ImageGrab.grab(bbox=region)
        img.save(path)
        return path
    except Exception as e: return f"Screenshot error: {e}"


def get_resolution() -> str:
    try:
        import ctypes
        user32 = ctypes.windll.user32
        w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        return f"{w}x{h}"
    except Exception:
        if _PIL:
            try:
                img = ImageGrab.grab()
                return f"{img.width}x{img.height}"
            except: pass
    return "Resolution unavailable."
