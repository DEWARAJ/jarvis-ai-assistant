"""Real keyboard & mouse control for JARVIS via pyautogui (typing, hotkeys, clicks).

Graceful: if pyautogui isn't installed, returns a clear 'pip install pyautogui' message
instead of crashing. This is what lets JARVIS type into windows and press keys for you.
"""
from __future__ import annotations
from tools.base_tool import BaseTool

_HINT = "Keyboard/mouse control needs one install: pip install pyautogui  (then restart JARVIS)."

# friendly key words -> pyautogui key names
KEYMAP = {"enter": "enter", "return": "enter", "tab": "tab", "escape": "esc", "esc": "esc",
          "space": "space", "backspace": "backspace", "delete": "delete", "win": "win",
          "windows": "win", "up": "up", "down": "down", "left": "left", "right": "right",
          "ctrl": "ctrl", "control": "ctrl", "alt": "alt", "shift": "shift", "home": "home",
          "end": "end", "pageup": "pageup", "pagedown": "pagedown", "f5": "f5"}


class InputControlTool(BaseTool):
    name = "input"; scope = "keyboard & mouse"

    def _pg(self):
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            return pyautogui
        except Exception:
            return None

    def type_text(self, text: str) -> dict:
        pg = self._pg()
        if not pg:
            return {"action": "type", "started": False, "spoken": _HINT, "debug": "no pyautogui"}
        if not text:
            return {"action": "type", "started": False, "spoken": "Type what?", "debug": ""}
        try:
            pg.typewrite(text, interval=0.01)
            return {"action": "type", "started": True, "spoken": "Typed it.", "debug": f"typed {len(text)} chars"}
        except Exception as e:
            return {"action": "type", "started": False, "spoken": f"I couldn't type that ({e}).", "debug": str(e)}

    def press(self, combo: str) -> dict:
        pg = self._pg()
        if not pg:
            return {"action": "press", "started": False, "spoken": _HINT, "debug": "no pyautogui"}
        keys = [KEYMAP.get(k.lower(), k.lower()) for k in combo.replace("+", " ").split() if k]
        if not keys:
            return {"action": "press", "started": False, "spoken": "Press what key?", "debug": ""}
        try:
            if len(keys) == 1:
                pg.press(keys[0])
            else:
                pg.hotkey(*keys)
            return {"action": "press", "started": True, "spoken": f"Pressed {' + '.join(keys)}.",
                    "debug": f"keys={keys}"}
        except Exception as e:
            return {"action": "press", "started": False, "spoken": f"I couldn't press that ({e}).", "debug": str(e)}

    def click(self, double: bool = False) -> dict:
        pg = self._pg()
        if not pg:
            return {"action": "click", "started": False, "spoken": _HINT, "debug": "no pyautogui"}
        try:
            pg.doubleClick() if double else pg.click()
            return {"action": "click", "started": True,
                    "spoken": "Double-clicked." if double else "Clicked.", "debug": "ok"}
        except Exception as e:
            return {"action": "click", "started": False, "spoken": f"I couldn't click ({e}).", "debug": str(e)}

    def move_mouse(self, x, y) -> dict:
        pg = self._pg()
        if not pg:
            return {"started": False, "spoken": _HINT, "debug": "no pyautogui"}
        try:
            pg.moveTo(int(x), int(y), duration=0.2)
            return {"started": True, "spoken": f"Moved the cursor to {x}, {y}, sir.", "debug": f"{x},{y}"}
        except Exception as e:
            return {"started": False, "spoken": f"I couldn't move the cursor ({e}).", "debug": str(e)}

    def click_at(self, x, y) -> dict:
        pg = self._pg()
        if not pg:
            return {"started": False, "spoken": _HINT, "debug": "no pyautogui"}
        try:
            pg.click(int(x), int(y))
            return {"started": True, "spoken": f"Clicked at {x}, {y}, sir.", "debug": f"{x},{y}"}
        except Exception as e:
            return {"started": False, "spoken": f"I couldn't click there ({e}).", "debug": str(e)}

    def right_click(self) -> dict:
        pg = self._pg()
        if not pg:
            return {"started": False, "spoken": _HINT, "debug": "no pyautogui"}
        try:
            pg.rightClick()
            return {"started": True, "spoken": "Right-clicked, sir.", "debug": "rightClick"}
        except Exception as e:
            return {"started": False, "spoken": f"I couldn't right-click ({e}).", "debug": str(e)}
