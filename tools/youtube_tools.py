"""YouTube / Media playback tool for JARVIS OS.

Three control layers (tried in order):
  1. Playwright in-page key press - most reliable when browser is JARVIS-controlled.
  2. OS virtual-key (VK) media keys - works system-wide for ANY audio/video app.
  3. pyautogui - spacebar / keyboard fallback when focus can be captured.
"""
from __future__ import annotations
import ctypes, os, sys, time, webbrowser, urllib.parse
from tools.base_tool import BaseTool

_VK_MEDIA_NEXT_TRACK  = 0xB0
_VK_MEDIA_PREV_TRACK  = 0xB1
_VK_MEDIA_STOP        = 0xB2
_VK_MEDIA_PLAY_PAUSE  = 0xB3
_KEYEVENTF_EXT        = 0x0001
_KEYEVENTF_UP         = 0x0002


def _vk(vk: int) -> bool:
    if sys.platform != "win32":
        return False
    try:
        u32 = ctypes.windll.user32
        u32.keybd_event(vk, 0, _KEYEVENTF_EXT, 0)
        time.sleep(0.05)
        u32.keybd_event(vk, 0, _KEYEVENTF_EXT | _KEYEVENTF_UP, 0)
        return True
    except Exception:
        return False


def _pg_press(key: str) -> bool:
    try:
        import pyautogui
        pyautogui.press(key)
        return True
    except Exception:
        return False


def _pg_hotkey(*keys: str) -> bool:
    try:
        import pyautogui
        pyautogui.hotkey(*keys)
        return True
    except Exception:
        return False


class YoutubeTool(BaseTool):
    name = "youtube"
    scope = "youtube and media playback"

    def __init__(self, context=None, logger=None):
        super().__init__(context, logger)
        self._pw = None
        self._pw_br = None

    def _browser_root(self):
        try:
            ctx = self.context or {}
            tools = ctx.get("tools")
            if tools:
                return tools.get("browser_root")
        except Exception:
            pass
        return None

    def _pw_key(self, key: str) -> bool:
        try:
            br = self._browser_root()
            if br:
                r = br._call("press", key, timeout=5)
                if r and not r.get("_error"):
                    return True
        except Exception:
            pass
        return False

    def _open(self, url: str) -> bool:
        try:
            if sys.platform.startswith("win"):
                os.startfile(url)
                return True
        except Exception:
            pass
        try:
            return webbrowser.open(url)
        except Exception:
            return False

    # PLAY

    def open_home(self) -> dict:
        ok = self._open("https://www.youtube.com")
        return {"started": ok,
                "spoken": "Here is YouTube, sir." if ok else "I could not open YouTube.",
                "debug": "home"}

    def search(self, query: str) -> dict:
        q = (query or "").strip()
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)
        ok = self._open(url)
        return {"started": ok, "url": url, "query": q,
                "spoken": "Searching YouTube for " + q + ", sir." if ok else "I could not open YouTube.",
                "debug": url}

    def play(self, query: str) -> dict:
        q = (query or "").strip()
        if not q:
            return {"started": False,
                    "spoken": "Play what, sir? For example: play Shape of You.",
                    "debug": ""}
        br = self._browser_root()
        if br:
            return br.youtube_play(q)
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)
        ok = self._open(url)
        return {"started": ok, "url": url,
                "spoken": "Here are the results for " + q + ", sir." if ok else "I could not open YouTube.",
                "debug": "no browser_root fallback"}

    # PAUSE / RESUME

    def pause_resume(self) -> dict:
        """Toggle play/pause. Tries: Playwright Space, OS VK, pyautogui space."""
        if self._pw_key("Space"):
            return {"started": True, "spoken": "Play/pause toggled, sir.", "debug": "playwright space"}
        if _vk(_VK_MEDIA_PLAY_PAUSE):
            return {"started": True, "spoken": "Play/pause toggled, sir.", "debug": "vk media_play_pause"}
        if _pg_press("space"):
            return {"started": True, "spoken": "Play/pause toggled, sir.", "debug": "pyautogui space"}
        return {"started": False,
                "spoken": "I could not toggle playback, sir. Try clicking the video first.",
                "debug": "all methods failed"}

    # NEXT / PREV

    def next_track(self) -> dict:
        """Skip to next. YouTube: Shift+N. OS VK fallback."""
        if self._pw_key("Shift+N"):
            return {"started": True, "spoken": "Next track, sir.", "debug": "playwright shift+n"}
        if _vk(_VK_MEDIA_NEXT_TRACK):
            return {"started": True, "spoken": "Next track, sir.", "debug": "vk next_track"}
        if _pg_hotkey("shift", "n"):
            return {"started": True, "spoken": "Next track, sir.", "debug": "pyautogui shift+n"}
        return {"started": False, "spoken": "I could not skip to the next track, sir.", "debug": "all methods failed"}

    def prev_track(self) -> dict:
        """Go to previous. YouTube: Shift+P. OS VK fallback."""
        if self._pw_key("Shift+P"):
            return {"started": True, "spoken": "Previous track, sir.", "debug": "playwright shift+p"}
        if _vk(_VK_MEDIA_PREV_TRACK):
            return {"started": True, "spoken": "Previous track, sir.", "debug": "vk prev_track"}
        if _pg_hotkey("shift", "p"):
            return {"started": True, "spoken": "Previous track, sir.", "debug": "pyautogui shift+p"}
        return {"started": False, "spoken": "I could not go to the previous track, sir.", "debug": "all methods failed"}

    # STOP

    def stop(self) -> dict:
        if _vk(_VK_MEDIA_STOP):
            return {"started": True, "spoken": "Playback stopped, sir.", "debug": "vk stop"}
        if self._pw_key("k"):
            return {"started": True, "spoken": "Playback stopped, sir.", "debug": "playwright k"}
        return {"started": False, "spoken": "I could not stop playback, sir.", "debug": "all methods failed"}

    # SEEK

    def seek_forward(self, seconds: int = 10) -> dict:
        """Seek forward. YouTube L = +10s."""
        presses = max(1, seconds // 10)
        ok = False
        for _ in range(presses):
            if self._pw_key("l") or _pg_press("l"):
                ok = True
        if not ok:
            for _ in range(max(1, seconds // 5)):
                ok = self._pw_key("ArrowRight") or _pg_press("right") or ok
        spoken = "Seeking forward " + str(seconds) + " seconds, sir." if ok \
                 else "I could not seek forward - the browser may not have focus, sir."
        return {"started": ok, "spoken": spoken, "debug": "seek fwd " + str(seconds) + "s"}

    def seek_back(self, seconds: int = 10) -> dict:
        """Seek backward. YouTube J = -10s."""
        presses = max(1, seconds // 10)
        ok = False
        for _ in range(presses):
            if self._pw_key("j") or _pg_press("j"):
                ok = True
        if not ok:
            for _ in range(max(1, seconds // 5)):
                ok = self._pw_key("ArrowLeft") or _pg_press("left") or ok
        spoken = "Rewinding " + str(seconds) + " seconds, sir." if ok \
                 else "I could not rewind - the browser may not have focus, sir."
        return {"started": ok, "spoken": spoken, "debug": "seek back " + str(seconds) + "s"}

    # FULLSCREEN

    def fullscreen(self) -> dict:
        """Toggle fullscreen. YouTube F key."""
        if self._pw_key("f"):
            return {"started": True, "spoken": "Toggling full screen, sir.", "debug": "playwright f"}
        if _pg_press("f"):
            return {"started": True, "spoken": "Toggling full screen, sir.", "debug": "pyautogui f"}
        if _pg_press("f11"):
            return {"started": True, "spoken": "Toggling full screen, sir.", "debug": "f11"}
        return {"started": False, "spoken": "I could not toggle full screen, sir.", "debug": "all methods failed"}

    # MUTE VIDEO

    def mute_video(self) -> dict:
        """Mute/unmute the video. YouTube M key."""
        if self._pw_key("m"):
            return {"started": True, "spoken": "Video muted/unmuted, sir.", "debug": "playwright m"}
        if _pg_press("m"):
            return {"started": True, "spoken": "Video muted/unmuted, sir.", "debug": "pyautogui m"}
        return {"started": False, "spoken": "I could not mute the video, sir.", "debug": "all methods failed"}

    # LIKE

    def like_video(self) -> dict:
        try:
            br = self._browser_root()
            if br:
                r = br._call("click_text", "Like", timeout=5)
                if r and not r.get("_error"):
                    return {"started": True, "spoken": "Liked the video, sir.", "debug": "playwright like button"}
        except Exception:
            pass
        return {"started": False,
                "spoken": "I could not like the video automatically, sir - the button may need a manual click.",
                "debug": "no reliable shortcut"}

    # LEGACY direct playwright play

    def _playwright_play(self, query: str):
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            return None
        try:
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
            if self._pw_br is not None:
                try: self._pw_br.close()
                except Exception: pass
            if self._pw is not None:
                try: self._pw.stop()
                except Exception: pass
            pw = sync_playwright().start()
            br = pw.chromium.launch(headless=False, args=["--autoplay-policy=no-user-gesture-required"])
            pg = br.new_page()
            pg.goto(url, timeout=20000)
            pg.wait_for_selector("a#video-title", timeout=8000)
            pg.click("a#video-title")
            pg.wait_for_load_state("domcontentloaded", timeout=15000)
            cur = pg.url
            self._pw = pw
            self._pw_br = br
            return cur if "/watch" in cur else None
        except Exception:
            return None
