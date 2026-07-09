"""System volume control for JARVIS OS.

Layers:
  1. pycaw (Windows Core Audio API) - exact % control, read current level.
  2. Windows virtual-key codes - no extra deps, coarse up/down.
  3. pyautogui - fallback press.
"""
from __future__ import annotations
import ctypes, sys, time
from tools.base_tool import BaseTool

_VK_VOLUME_UP   = 0xAF
_VK_VOLUME_DOWN = 0xAE
_VK_VOLUME_MUTE = 0xAD
_KEYEVENTF_EXT  = 0x0001
_KEYEVENTF_UP   = 0x0002


def _send_vk(vk: int, times: int = 1) -> bool:
    if sys.platform != "win32":
        return False
    try:
        u32 = ctypes.windll.user32
        for _ in range(times):
            u32.keybd_event(vk, 0, _KEYEVENTF_EXT, 0)
            time.sleep(0.04)
            u32.keybd_event(vk, 0, _KEYEVENTF_EXT | _KEYEVENTF_UP, 0)
        return True
    except Exception:
        return False


def _pg_press(key: str, times: int = 1) -> bool:
    try:
        import pyautogui
        for _ in range(times):
            pyautogui.press(key)
        return True
    except Exception:
        return False


def _get_pycaw_volume():
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current = volume.GetMasterVolumeLevelScalar()
        return volume, current
    except Exception:
        return None, None


class VolumeControlTool(BaseTool):
    name = "volume"
    scope = "system volume"

    def up(self) -> dict:
        ok = _send_vk(_VK_VOLUME_UP, 5) or _pg_press("volumeup", 5)
        return {
            "started": ok,
            "spoken": "Volume raised, sir." if ok else "I could not raise the volume.",
            "debug": "vk volumeup x5",
        }

    def down(self) -> dict:
        ok = _send_vk(_VK_VOLUME_DOWN, 5) or _pg_press("volumedown", 5)
        return {
            "started": ok,
            "spoken": "Volume lowered, sir." if ok else "I could not lower the volume.",
            "debug": "vk volumedown x5",
        }

    def mute(self) -> dict:
        ok = _send_vk(_VK_VOLUME_MUTE) or _pg_press("volumemute")
        return {
            "started": ok,
            "spoken": "Muted, sir." if ok else "I could not mute.",
            "debug": "vk mute",
        }

    def unmute(self) -> dict:
        ok = _send_vk(_VK_VOLUME_MUTE) or _pg_press("volumemute")
        return {
            "started": ok,
            "spoken": "Unmuted, sir." if ok else "I could not unmute.",
            "debug": "vk unmute (toggle)",
        }

    def set_volume(self, level: int) -> dict:
        """Set volume to an exact percentage (0-100)."""
        level = max(0, min(100, int(level)))
        vol_iface, current = _get_pycaw_volume()
        if vol_iface is not None:
            try:
                vol_iface.SetMasterVolumeLevelScalar(level / 100.0, None)
                return {
                    "started": True,
                    "spoken": "Volume set to " + str(level) + " percent, sir.",
                    "debug": "pycaw exact " + str(level) + "%",
                }
            except Exception:
                pass
        if sys.platform == "win32":
            try:
                _send_vk(_VK_VOLUME_DOWN, 50)
                time.sleep(0.1)
                presses = level // 2
                if presses:
                    _send_vk(_VK_VOLUME_UP, presses)
                return {
                    "started": True,
                    "spoken": "Volume set to approximately " + str(level) + " percent, sir.",
                    "debug": "vk coarse " + str(presses) + " presses",
                }
            except Exception:
                pass
        return {
            "started": False,
            "spoken": "I could not set the volume precisely. Install pycaw for exact control.",
            "debug": "no pycaw, vk failed",
        }

    def get_level(self) -> dict:
        """Report current volume level."""
        _, current = _get_pycaw_volume()
        if current is not None:
            pct = round(current * 100)
            return {
                "started": True,
                "spoken": "Volume is at " + str(pct) + " percent, sir.",
                "debug": "pycaw " + str(pct) + "%",
                "level": pct,
            }
        return {
            "started": False,
            "spoken": "I could not read the volume level. Install pycaw for this feature.",
            "debug": "no pycaw",
            "level": None,
        }
