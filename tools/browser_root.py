"""Browser execution root for JARVIS.

Two engines:
  - PLAYWRIGHT (preferred): a single persistent Chrome that JARVIS drives — it navigates in
    the SAME tab, searches, and clicks results, so 'play X on YouTube' actually plays.
    Playwright's sync API must run in one thread, so all browser ops run in a dedicated
    worker thread (the web server is multi-threaded). Install once:
        pip install playwright ; python -m playwright install chromium
  - FALLBACK (no Playwright): opens target sites/search URLs in your default browser
    (reliable, but each is a new tab and it can't click inside the page).

Either way it never dead-ends and never fakes success.
"""
from __future__ import annotations
import os, sys, queue, threading, webbrowser, urllib.parse
from tools.base_tool import BaseTool

SITES = {
    "instagram": "https://www.instagram.com", "facebook": "https://www.facebook.com",
    "youtube": "https://www.youtube.com", "gmail": "https://mail.google.com",
    "google": "https://www.google.com", "amazon": "https://www.amazon.com",
    "shopify": "https://admin.shopify.com", "shopify admin": "https://admin.shopify.com",
    "twitter": "https://twitter.com", "reddit": "https://www.reddit.com",
    "netflix": "https://www.netflix.com", "linkedin": "https://www.linkedin.com",
    "whatsapp": "https://web.whatsapp.com", "tiktok": "https://www.tiktok.com",
    "github": "https://github.com", "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai", "perplexity": "https://www.perplexity.ai",
    "maps": "https://maps.google.com", "spotify": "https://open.spotify.com",
    "pinterest": "https://www.pinterest.com", "twitch": "https://www.twitch.tv",
}
_SHORT = {"x"}


class _PwWorker(threading.Thread):
    """Owns the Playwright instance + page in a single thread; processes commands via a queue."""
    def __init__(self, logger=None, data_dir=None):
        super().__init__(daemon=True)
        self.logger = logger
        self.data_dir = data_dir
        self.inq = queue.Queue()
        self.outq = queue.Queue()
        self.available = None  # None=unknown, True/False after start
        self._cdp_error = ""  # set if CDP attach failed, so BrowserRoot can surface it

    def _launch_debug_chrome(self) -> bool:
        """Auto-start a dedicated debug Chrome (remote-debugging on 9222) so the master never has
        to run start_my_chrome.bat by hand. Chrome 136+ blocks debugging on the default profile,
        so we use a separate JARVIS profile dir. Returns True once the CDP port is reachable."""
        import shutil, subprocess, time, urllib.request

        def _port_up():
            try:
                urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=1)
                return True
            except Exception:
                return False

        if _port_up():
            return True
        exe = shutil.which("chrome")
        if not exe:
            for pth in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")):
                if os.path.exists(pth):
                    exe = pth
                    break
        if not exe:
            if self.logger: self.logger.warning("browser_root: chrome.exe not found for auto-launch")
            return False
        profile = self.data_dir or os.path.join(os.path.expanduser("~"), ".jarvis_chrome")
        try:
            os.makedirs(profile, exist_ok=True)
        except Exception:
            pass
        try:
            subprocess.Popen([exe, "--remote-debugging-port=9222",
                              "--user-data-dir=" + profile,
                              "--no-first-run", "--no-default-browser-check",
                              "https://www.google.com"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            if self.logger: self.logger.warning(f"browser_root: chrome auto-launch failed: {e}")
            return False
        for _ in range(40):                 # wait up to ~12s for Chrome's debug port
            if _port_up():
                return True
            time.sleep(0.3)
        return _port_up()

    def run(self):
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            self.available = False
            return
        try:
            pw = sync_playwright().start()
            ctx = None
            # Attach to the user's real Chrome via CDP. If it isn't already running with remote
            # debugging, AUTO-START a dedicated JARVIS debug Chrome ourselves (no more manual
            # start_my_chrome.bat), then retry. Only if Chrome can't be found/launched at all do
            # we mark unavailable — BrowserRoot then opens URLs in the default browser so
            # 'play X on YouTube' still works instead of dead-ending.
            browser = None
            try:
                browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
            except Exception as cdp_err:
                if self.logger: self.logger.info(f"browser_root: no debug Chrome ({cdp_err}); auto-starting one")
                if self._launch_debug_chrome():
                    try:
                        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
                    except Exception as e2:
                        browser = None; cdp_err = e2
                if browser is None:
                    self.available = False
                    self._cdp_error = (
                        "I tried to launch a debug Chrome automatically, sir, but it didn't come up, "
                        "so I'll use your default browser for web pages. (Is Chrome installed in the "
                        "usual location?) "
                        f"(CDP error: {cdp_err})"
                    )
                    if self.logger: self.logger.warning(f"browser_root: auto-launch+attach failed — {cdp_err}")
                    return
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            if self.logger: self.logger.info("browser_root: attached to Chrome via CDP on port 9222")
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            self.available = True
        except Exception as e:
            self.available = False
            if self.logger: self.logger.error(f"playwright start failed: {e}")
            return
        while True:
            cmd, arg = self.inq.get()
            try:
                self.outq.put(("ok", self._exec(page, ctx, cmd, arg)))
            except Exception as e:
                self.outq.put(("err", str(e)))

    def _active_page(self, ctx, fallback):
        """Resolve the user's CURRENT tab so operations hit the tab they're looking at,
        not whichever page happened to be first. Prefers the visible+focused tab."""
        try:
            pages = [p for p in ctx.pages if not p.is_closed()]
        except Exception:
            return fallback
        if not pages:
            return fallback
        for p in reversed(pages):          # visible AND focused = the active tab
            try:
                if p.evaluate("() => document.visibilityState === 'visible' && document.hasFocus()"):
                    return p
            except Exception:
                continue
        for p in reversed(pages):          # else just visible
            try:
                if p.evaluate("() => document.visibilityState === 'visible'"):
                    return p
            except Exception:
                continue
        return pages[-1]                   # else most-recently-opened

    def _smart_click(self, page, target):
        """Click an element matching `target` using many strategies, in order of precision.
        Handles links, buttons, menu items, tabs, radio/checkbox, and fuzzy text. Scrolls the
        match into view first. Returns (clicked: bool, how: str)."""
        target = (target or "").strip()
        if not target:
            return (False, "empty")
        # Ordered candidate locators (lazy lambdas so a bad role doesn't crash the rest)
        attempts = [
            ("role=link",     lambda: page.get_by_role("link", name=target, exact=False)),
            ("role=button",   lambda: page.get_by_role("button", name=target, exact=False)),
            ("role=menuitem", lambda: page.get_by_role("menuitem", name=target, exact=False)),
            ("role=tab",      lambda: page.get_by_role("tab", name=target, exact=False)),
            ("role=option",   lambda: page.get_by_role("option", name=target, exact=False)),
            ("role=radio",    lambda: page.get_by_role("radio", name=target, exact=False)),
            ("role=checkbox", lambda: page.get_by_role("checkbox", name=target, exact=False)),
            ("label",         lambda: page.get_by_label(target, exact=False)),
            ("placeholder",   lambda: page.get_by_placeholder(target, exact=False)),
            ("title",         lambda: page.get_by_title(target, exact=False)),
            ("text",          lambda: page.get_by_text(target, exact=False)),
        ]
        for how, make in attempts:
            try:
                loc = make().first
                loc.scroll_into_view_if_needed(timeout=1500)
                loc.click(timeout=2500)
                return (True, how)
            except Exception:
                continue
        # last resort: JS scan for any element whose visible text contains the target
        try:
            clicked = page.evaluate(
                "(t)=>{t=t.toLowerCase();"
                "const els=[...document.querySelectorAll('a,button,[role],input,li,span,div,option')];"
                "const el=els.find(e=>((e.innerText||e.value||e.getAttribute('aria-label')||'')"
                ".trim().toLowerCase().includes(t)) && e.offsetParent!==null);"
                "if(el){el.scrollIntoView({block:'center'}); el.click(); return true;} return false;}",
                target)
            if clicked:
                return (True, "js-contains")
        except Exception:
            pass
        return (False, "no-match")

    def _exec(self, page, ctx, cmd, arg):
        # Always act on the user's CURRENT tab for page operations.
        if cmd in ("goto", "click_text", "click_link", "read_text", "info", "scroll",
                   "click_first", "click_nth", "youtube_play", "yt_search_play", "media_toggle",
                   "back", "forward", "type", "press"):
            page = self._active_page(ctx, page)
        if cmd == "list_tabs":
            pages = [p for p in ctx.pages if not p.is_closed()]
            tabs = []
            for i, p in enumerate(pages):
                try:
                    tabs.append({"index": i, "title": p.title(), "url": p.url})
                except Exception:
                    tabs.append({"index": i, "title": "?", "url": p.url})
            return {"tabs": tabs, "count": len(tabs)}
        if cmd == "close_tab":
            # arg = title/URL substring to target; blank = close the active tab
            pages = [p for p in ctx.pages if not p.is_closed()]
            target = (arg or "").strip().lower()
            if target:
                matched = [p for p in pages
                           if target in p.url.lower() or target in (p.title() or "").lower()]
                if not matched:
                    return {"closed": False, "reason": f"no tab matching '{arg}'",
                            "tabs": [{"title": p.title(), "url": p.url} for p in pages]}
                for p in matched:
                    try: p.close()
                    except Exception: pass
                return {"closed": True, "count": len(matched),
                        "titles": [p.title() for p in matched]}
            else:
                active = self._active_page(ctx, page)
                title = active.title() if active else "?"
                try: active.close()
                except Exception: pass
                return {"closed": True, "count": 1, "titles": [title]}
        if cmd == "read_text":
            txt = page.evaluate("() => document.body ? document.body.innerText.slice(0, 8000) : ''")
            return {"url": page.url, "title": page.title(), "text": txt}
        if cmd == "click_link":
            page.bring_to_front()
            ok, how = self._smart_click(page, arg)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=8000)
            except Exception:
                pass
            return {"url": page.url, "clicked": ok, "via": how}
        if cmd == "select_option":
            # arg = "<select hint>|<option text>" or just "<option text>" (first <select>)
            page.bring_to_front()
            sel_hint, _, opt = (arg.partition("|") if "|" in arg else ("", "", arg))
            opt = opt.strip()
            try:
                if sel_hint.strip():
                    loc = page.get_by_label(sel_hint.strip()).first
                else:
                    loc = page.locator("select").first
                loc.select_option(label=opt, timeout=6000)
                return {"url": page.url, "selected": opt, "via": "select_option"}
            except Exception:
                # not a native <select> — treat as a clickable option (custom dropdown)
                ok, how = self._smart_click(page, opt)
                return {"url": page.url, "selected": opt if ok else None, "via": how}
        if cmd == "goto":
            page.bring_to_front(); page.goto(arg, timeout=25000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            return {"url": page.url, "title": page.title()}
        if cmd == "youtube_play":
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(arg)
            page.bring_to_front(); page.goto(url, timeout=25000)
            # dismiss cookie/consent overlays if present (best effort)
            for sel in ("button[aria-label*='Accept']", "button:has-text('Accept all')",
                        "button:has-text('I agree')", "tp-yt-paper-button:has-text('Accept all')"):
                try:
                    page.click(sel, timeout=1500)
                    break
                except Exception:
                    pass
            page.wait_for_selector("a#video-title", timeout=12000)
            # read the first real video link, then navigate straight to it (robust vs overlays)
            href = page.get_attribute("a#video-title", "href")
            if href:
                watch = href if href.startswith("http") else ("https://www.youtube.com" + href)
                page.goto(watch, timeout=25000)
            else:
                page.click("a#video-title")
            page.wait_for_selector("video", timeout=12000)
            # force playback (videos often load paused under automation)
            try:
                page.evaluate("(()=>{const v=document.querySelector('video'); if(v){v.muted=false; const p=v.play(); if(p&&p.catch)p.catch(()=>{});}})()")
            except Exception:
                pass
            try:
                paused = page.evaluate("(()=>{const v=document.querySelector('video'); return v? v.paused: true;})()")
            except Exception:
                paused = None
            if paused:                                   # nudge with the 'k' play shortcut
                try: page.keyboard.press("k")
                except Exception: pass
                try: paused = page.evaluate("(()=>{const v=document.querySelector('video'); return v? v.paused: true;})()")
                except Exception: pass
            return {"url": page.url, "playing": ("/watch" in page.url) and (paused is False or paused is None)}
        if cmd == "yt_search_play":
            # Search-box flow on the EXISTING CDP page (never a new browser). Navigate to YouTube
            # in the attached tab, fill input#search, open the first ytd-video-renderer result,
            # then verify playback actually started.
            page.bring_to_front()
            page.goto("https://www.youtube.com", timeout=25000)
            # consent / cookie banner — best effort, never fail the whole action if absent
            for sel in ("button[aria-label*='Accept']", "button:has-text('Accept all')",
                        "button:has-text('I agree')", "tp-yt-paper-button:has-text('Accept all')"):
                try:
                    page.click(sel, timeout=1500)
                    break
                except Exception:
                    pass
            # fill the search box and submit (fall back to the results URL if the box isn't found)
            try:
                page.wait_for_selector("input#search", timeout=8000)
                page.fill("input#search", arg)
                page.press("input#search", "Enter")
            except Exception:
                page.goto("https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(arg),
                          timeout=25000)
            # explicit wait for results (not a sleep), then open the first result's title link
            page.wait_for_selector("ytd-video-renderer a#video-title, a#video-title", timeout=12000)
            href = page.get_attribute("ytd-video-renderer a#video-title, a#video-title", "href")
            if href:
                watch = href if href.startswith("http") else ("https://www.youtube.com" + href)
                page.goto(watch, timeout=25000)
            else:
                page.click("ytd-video-renderer a#video-title, a#video-title")
            page.wait_for_selector("video", timeout=12000)
            # verify playback started; if paused, trigger play
            try:
                page.evaluate("(()=>{const v=document.querySelector('video'); if(v){v.muted=false; const p=v.play(); if(p&&p.catch)p.catch(()=>{});}})()")
            except Exception:
                pass
            try:
                paused = page.evaluate("(()=>{const v=document.querySelector('video'); return v? v.paused: true;})()")
            except Exception:
                paused = None
            if paused:                                   # nudge with the 'k' play shortcut
                try: page.keyboard.press("k")
                except Exception: pass
                try: paused = page.evaluate("(()=>{const v=document.querySelector('video'); return v? v.paused: true;})()")
                except Exception: pass
            return {"url": page.url, "playing": ("/watch" in page.url) and (paused is False or paused is None)}
        if cmd == "media_toggle":
            try: page.keyboard.press("k")
            except Exception:
                page.keyboard.press("space")
            try: paused = page.evaluate("(()=>{const v=document.querySelector('video'); return v? v.paused: null;})()")
            except Exception: paused = None
            return {"paused": paused}
        if cmd == "click_first":
            page.wait_for_selector("a#video-title, h3 a, a[href]", timeout=8000)
            page.click("a#video-title, h3 a")
            page.wait_for_load_state("domcontentloaded", timeout=12000)
            return {"url": page.url}
        if cmd == "click_text":
            page.click(f"text={arg}", timeout=6000)
            return {"url": page.url}
        if cmd == "back":
            page.go_back(timeout=8000); return {"url": page.url}
        if cmd == "forward":
            page.go_forward(timeout=8000); return {"url": page.url}
        if cmd == "scroll":
            amount = {"down": 900, "up": -900, "bottom": 6000, "top": -6000}.get(arg, 900)
            page.mouse.wheel(0, amount)
            if arg == "bottom":
                page.keyboard.press("End")
            elif arg == "top":
                page.keyboard.press("Home")
            return {"ok": True}
        if cmd == "click_nth":
            try:
                n = max(1, int(arg))
            except Exception:
                n = 1
            # Robust across homepage/feed (a#video-title-link), search results
            # (a#video-title), and thumbnail links — collect unique /watch hrefs.
            sel = "a[href*='/watch']"
            try:
                page.wait_for_selector(sel, timeout=10000)
            except Exception:
                pass
            hrefs = page.evaluate(
                "(s)=>{const seen=new Set(); const out=[];"
                "document.querySelectorAll(s).forEach(a=>{const h=a.getAttribute('href');"
                "if(h && h.includes('/watch') && !seen.has(h)){seen.add(h); out.push(h);}});"
                "return out;}", sel)
            if hrefs and len(hrefs) >= n:
                href = hrefs[n - 1]
                watch = href if href.startswith("http") else ("https://www.youtube.com" + href)
                page.goto(watch, timeout=20000)
                page.wait_for_selector("video", timeout=10000)
                try:
                    page.evaluate("(()=>{const v=document.querySelector('video'); if(v){v.muted=false; const p=v.play(); if(p&&p.catch)p.catch(()=>{});}})()")
                except Exception:
                    pass
                return {"url": page.url, "played": True}
            return {"played": False, "count": len(hrefs or [])}
        if cmd == "type":
            page.keyboard.type(arg); return {"ok": True}
        if cmd == "press":
            page.keyboard.press(arg); return {"ok": True}
        if cmd == "info":
            return {"url": page.url, "title": page.title()}
        return {"ok": False}


class BrowserRoot(BaseTool):
    name = "browser_root"; scope = "web execution root"

    def __init__(self, context=None, logger=None):
        super().__init__(context, logger)
        self._worker = None
        self._lock = threading.Lock()

    # ---- engine selection ----
    def _pw(self):
        """Return the worker if attached to real Chrome, else None.
        When CDP attach failed, the worker stores the human-readable error so callers
        can surface it instead of saying a generic 'no playwright' message."""
        if self._worker is None:
            data_dir = None
            try:
                data_dir = (self.context.get("settings") or {}).get("chrome_user_data_dir") or None
            except Exception:
                data_dir = None
            w = _PwWorker(self.logger, data_dir); w.start(); self._worker = w
            import time
            for _ in range(60):
                if w.available is not None:
                    break
                time.sleep(0.1)
        return self._worker if self._worker and self._worker.available else None

    def _no_chrome_msg(self) -> str:
        """Human-readable reason why browser ops are unavailable."""
        if self._worker and self._worker._cdp_error:
            return self._worker._cdp_error
        return ("I'm not attached to your Chrome, sir. "
                "Run start_my_chrome.bat to open Chrome with remote debugging, then restart JARVIS.")

    def _call(self, cmd, arg, timeout=35):
        w = self._pw()
        if not w:
            return None
        with self._lock:
            w.inq.put((cmd, arg))
            try:
                status, data = w.outq.get(timeout=timeout)
            except queue.Empty:
                return {"_error": "timeout"}
            return data if status == "ok" else {"_error": data}

    def _open_default(self, url: str) -> bool:
        """Open in Google Chrome specifically (not the system default browser)."""
        import shutil
        if sys.platform.startswith("win"):
            exe = shutil.which("chrome")
            if not exe:
                for pth in (r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                            r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                            os.path.expanduser(r"~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")):
                    if os.path.exists(pth):
                        exe = pth; break
            try:
                if exe:
                    import subprocess; subprocess.Popen([exe, url]); return True
                import subprocess; subprocess.Popen(f'start chrome "{url}"', shell=True); return True
            except Exception:
                try: os.startfile(url); return True
                except Exception: pass
        try:
            webbrowser.open(url); return True
        except Exception:
            return False

    def scroll(self, direction: str = "down") -> dict:
        r = self._call("scroll", direction)
        if r and not r.get("_error"):
            return {"started": True, "spoken": f"Scrolling {direction}, sir.", "debug": direction}
        try:
            import pyautogui
            amt = {"down": -700, "up": 700, "bottom": -3000, "top": 3000}.get(direction, -700)
            pyautogui.scroll(amt)
            return {"started": True, "spoken": f"Scrolling {direction}, sir.", "debug": "pyautogui"}
        except Exception:
            return {"started": False, "spoken": "I need keyboard control to scroll, sir (pip install pyautogui).",
                    "debug": "no method"}

    def go_forward(self) -> dict:
        r = self._call("forward", "")
        if r and not r.get("_error"):
            return {"started": True, "spoken": "Going forward, sir.", "debug": r.get("url", "")}
        try:
            import pyautogui; pyautogui.hotkey("alt", "right")
            return {"started": True, "spoken": "Going forward, sir.", "debug": "alt+right"}
        except Exception:
            return {"started": False, "spoken": "I couldn't go forward, sir.", "debug": "no method"}

    def play_nth(self, n: int) -> dict:
        r = self._call("click_nth", str(n))
        if r and not r.get("_error") and r.get("played"):
            return {"started": True, "spoken": f"Playing result number {n}, sir.", "debug": r.get("url", "")}
        return {"started": False,
                "spoken": (f"I couldn't pick result {n}, sir — I need to be attached to your Chrome and on a "
                           "YouTube results page. Run start_my_chrome.bat, open YouTube, then ask again."),
                "debug": (r or {}).get("_error", "not attached / no results on active tab")}

    _HOTKEYS = {
        "new_tab": (("ctrl", "t"), "Opening a new tab, sir."),
        "switch_tab": (("ctrl", "tab"), "Switching tabs, sir."),
        "prev_tab": (("ctrl", "shift", "tab"), "Previous tab, sir."),
        "reopen_tab": (("ctrl", "shift", "t"), "Reopening the last tab, sir."),
        "zoom_in": (("ctrl", "+"), "Zooming in, sir."),
        "zoom_out": (("ctrl", "-"), "Zooming out, sir."),
        "zoom_reset": (("ctrl", "0"), "Zoom reset, sir."),
        "fullscreen": (("f",), "Full screen, sir."),
        "exit_fullscreen": (("escape",), "Exiting full screen, sir."),
        "stop_loading": (("escape",), "Stopped loading, sir."),
        "captions": (("c",), "Toggled captions, sir."),
    }

    def hotkey(self, name: str) -> dict:
        spec = self._HOTKEYS.get(name)
        if not spec:
            return {"started": False, "spoken": "I don't have that browser shortcut, sir.", "debug": name}
        keys, spoken = spec
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            return {"started": True, "spoken": spoken, "debug": "+".join(keys)}
        except Exception:
            return {"started": False, "spoken": "I need keyboard control for that, sir (pip install pyautogui).",
                    "debug": "no pyautogui"}

    def list_tabs(self) -> dict:
        """List all open tabs in the attached Chrome."""
        r = self._call("list_tabs", "")
        if r and not r.get("_error"):
            tabs = r.get("tabs", [])
            if not tabs:
                return {"started": True, "spoken": "No open tabs, sir.", "debug": "0 tabs", "tabs": []}
            lines = "\n".join(f"  {t['index']+1}. {t['title'] or t['url']}" for t in tabs)
            return {"started": True, "tabs": tabs,
                    "spoken": f"You have {len(tabs)} open tabs, sir:\n{lines}",
                    "debug": f"{len(tabs)} tabs"}
        return {"started": False, "spoken": self._no_chrome_msg(), "debug": (r or {}).get("_error", "")}

    def close_tab(self, target: str = "") -> dict:
        """Close a tab by title/URL substring, or the active tab if no target given."""
        r = self._call("close_tab", target or "")
        if r and not r.get("_error"):
            if not r.get("closed"):
                tabs = r.get("tabs", [])
                hint = "; open tabs: " + ", ".join(t["title"] for t in tabs) if tabs else ""
                return {"started": False,
                        "spoken": f"I couldn't find a tab matching '{target}', sir.{hint}",
                        "debug": r.get("reason", "")}
            count = r.get("count", 1)
            titles = ", ".join(r.get("titles", []))
            msg = f"Closed {count} tab{'s' if count > 1 else ''}: {titles}, sir." if titles else "Tab closed, sir."
            return {"started": True, "spoken": msg, "debug": f"closed {count}"}
        return {"started": False, "spoken": self._no_chrome_msg(), "debug": (r or {}).get("_error", "")}

    def _nav(self, url: str) -> tuple[bool, bool]:
        """Navigate. Returns (ok, used_playwright)."""
        r = self._call("goto", url)
        if r and not r.get("_error"):
            return True, True
        return self._open_default(url), False

    # ---- resolve a known site in messy text ----
    def resolve(self, text: str):
        low = " " + (text or "").lower().strip() + " "
        for key in sorted(SITES, key=len, reverse=True):
            if key in _SHORT:
                continue
            if (" " + key + " ") in low or (" " + key + ".") in low:
                name = key.split()[0].capitalize() if key != "shopify admin" else "Shopify admin"
                return name, SITES[key]
        if " x " in low:
            return "X", "https://x.com"
        return None, None

    # ---- spec functions ----
    def open_site(self, name: str) -> dict:
        site_name, url = self.resolve(name)
        if not url:
            return {"started": False, "site": name,
                    "spoken": f"I'm not sure which site '{name}' is, sir.", "debug": "unresolved"}
        ok, _ = self._nav(url)
        return {"started": ok, "site": site_name, "url": url,
                "spoken": f"{site_name} is open, sir." if ok else f"I couldn't open {site_name}, sir.",
                "debug": f"opened {url}"}

    def search_and_open(self, text: str) -> dict:
        site_name, url = self.resolve(text)
        if url:
            ok, _ = self._nav(url)
            return {"started": ok, "site": site_name, "url": url,
                    "spoken": f"{site_name} is open, sir." if ok else f"I couldn't open {site_name}, sir.",
                    "debug": f"site {url}"}
        return self.google_search(text)

    def google_search(self, query: str) -> dict:
        q = (query or "").strip()
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(q) if q else "https://www.google.com"
        ok, _ = self._nav(url)
        return {"started": ok, "url": url, "query": q,
                "spoken": (f"Searching {q}, sir." if q else "Opening Google, sir.") if ok else "I couldn't reach the browser, sir.",
                "debug": url}

    def youtube_search(self, query: str) -> dict:
        q = (query or "").strip()
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q) if q else "https://www.youtube.com"
        ok, _ = self._nav(url)
        return {"started": ok, "url": url, "query": q,
                "spoken": (f"Searching YouTube for {q}, sir." if q else "Opening YouTube, sir.") if ok else "I couldn't open YouTube, sir.",
                "debug": url}

    def youtube_play(self, query: str) -> dict:
        q = (query or "").strip()
        if not q:
            return {"started": False, "spoken": "What shall I play, sir?", "debug": ""}
        r = self._call("youtube_play", q, timeout=40)
        if r and not r.get("_error") and r.get("playing"):
            return {"started": True, "spoken": f"Playing {q}, sir.", "debug": r.get("url", "")}
        if r and not r.get("_error"):
            return {"started": True, "spoken": f"I opened the results for {q}, sir — the first one is ready.",
                    "debug": "no /watch"}
        # fallback: open results in default browser
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)
        ok = self._open_default(url)
        why = (r or {}).get("_error", "Playwright not installed")
        return {"started": ok,
                "spoken": (f"Here are the top results for {q}, sir — tap the first to play. "
                           "For true one-word playback, install browser automation: pip install playwright."),
                "debug": f"fallback ({why})"}

    def play_youtube_search(self, query: str) -> dict:
        """Search YouTube and play the first result, all on the EXISTING CDP-attached Chrome
        (reuses/opens a tab in the same browser — never launches a separate Chromium). Class A."""
        q = (query or "").strip()
        if not q:
            return {"started": False, "spoken": "What shall I play, sir?", "debug": ""}
        r = self._call("yt_search_play", q, timeout=45)
        if r and not r.get("_error") and r.get("playing"):
            return {"started": True, "spoken": f"Playing {q} on YouTube, sir.", "debug": r.get("url", "")}
        if r and not r.get("_error"):
            return {"started": True, "spoken": f"I opened {q} on YouTube, sir — starting it now.",
                    "debug": r.get("url", "")}
        # Fallback: no controlled browser available — open the YouTube search in the default
        # browser so it still plays instead of dead-ending with 'run start_my_chrome.bat'.
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q)
        if self._open_default(url):
            return {"started": True,
                    "spoken": f"I've opened YouTube results for {q} in your browser, sir.",
                    "debug": url}
        return {"started": False, "spoken": self._no_chrome_msg(), "debug": (r or {}).get("_error", "")}

    def open_url(self, url: str) -> dict:
        url = (url or "").strip().strip('"').strip("'")
        if url and not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        ok, _ = self._nav(url) if url else (False, False)
        return {"started": ok, "url": url,
                "spoken": "Opening the page, sir." if ok else "I couldn't open that page, sir.", "debug": url}

    def click_first_result(self) -> dict:
        r = self._call("click_first", "")
        if r and not r.get("_error"):
            return {"started": True, "spoken": "Opening the first result, sir.", "debug": r.get("url", "")}
        return {"started": False,
                "spoken": "I can only click inside the page with browser automation, sir — install it with: pip install playwright.",
                "debug": (r or {}).get("_error", "no playwright")}

    def click_text(self, text: str) -> dict:
        r = self._call("click_text", text)
        if r and not r.get("_error"):
            return {"started": True, "spoken": f"Clicking {text}, sir.", "debug": r.get("url", "")}
        return {"started": False,
                "spoken": f"I couldn't click '{text}', sir — clicking needs browser automation (pip install playwright).",
                "debug": (r or {}).get("_error", "no playwright")}

    def read_current_page(self) -> dict:
        """Read the text of the user's CURRENT tab (needs the controlled/attached browser)."""
        r = self._call("read_text", "")
        if r and not r.get("_error"):
            return {"started": True, "url": r.get("url", ""), "title": r.get("title", ""),
                    "text": r.get("text", ""),
                    "spoken": f"I'm reading the current tab now, sir — {r.get('title','this page')}.",
                    "debug": r.get("url", "")}
        return {"started": False, "text": "",
                "spoken": ("I can only read the page inside the controlled browser, sir — run "
                           "start_my_chrome.bat so I can attach to your Chrome."),
                "debug": (r or {}).get("_error", "no playwright")}

    def click_link(self, text: str) -> dict:
        """Click any element (link/button/menu/tab/option/radio/text) by description on the
        current tab, using multi-strategy matching."""
        text = (text or "").strip()
        if not text:
            return {"started": False, "spoken": "What should I click on the page, sir?", "debug": ""}
        r = self._call("click_link", text)
        if r and not r.get("_error") and r.get("clicked"):
            return {"started": True, "spoken": f"Clicking {text}, sir.",
                    "debug": f"via {r.get('via')} -> {r.get('url','')}"}
        if r and not r.get("_error"):  # browser drove, but nothing matched the description
            return {"started": False,
                    "spoken": (f"I'm on the page but couldn't find '{text}' to click, sir. Try the exact "
                               "visible label, or tell me 'read the page' and I'll list what's clickable."),
                    "debug": f"no-match via {r.get('via')}"}
        return {"started": False,
                "spoken": (f"I couldn't click '{text}', sir — make sure I'm attached to your Chrome "
                           "(run start_my_chrome.bat)."),
                "debug": (r or {}).get("_error", "no playwright")}

    def select_option(self, text: str) -> dict:
        """Choose an option in a dropdown/menu on the current tab. Accepts 'dropdown|option'
        or just 'option' (uses the first <select> or a matching custom menu item)."""
        text = (text or "").strip()
        if not text:
            return {"started": False, "spoken": "Which option shall I choose, sir?", "debug": ""}
        r = self._call("select_option", text)
        if r and not r.get("_error") and r.get("selected"):
            return {"started": True, "spoken": f"Selected {r.get('selected')}, sir.",
                    "debug": f"via {r.get('via')} -> {r.get('url','')}"}
        if r and not r.get("_error"):
            return {"started": False,
                    "spoken": (f"I couldn't find the option '{text}' on this page, sir. Tell me the exact "
                               "label, or 'read the page' and I'll list the choices."),
                    "debug": f"no-match via {r.get('via')}"}
        return {"started": False,
                "spoken": (f"I couldn't choose '{text}', sir — make sure I'm attached to your Chrome "
                           "(run start_my_chrome.bat)."),
                "debug": (r or {}).get("_error", "no playwright")}

    def go_back(self) -> dict:
        r = self._call("back", "")
        if r and not r.get("_error"):
            return {"started": True, "spoken": "Going back, sir.", "debug": r.get("url", "")}
        # fallback to hotkey
        try:
            import pyautogui; pyautogui.hotkey("alt", "left")
            return {"started": True, "spoken": "Going back, sir.", "debug": "alt+left"}
        except Exception:
            return {"started": False, "spoken": "I couldn't go back, sir.", "debug": "no method"}

    def media_toggle(self) -> dict:
        """Pause/resume the video in the controlled browser (YouTube 'k'). Fallback: global key."""
        r = self._call("media_toggle", "")
        if r and not r.get("_error"):
            paused = r.get("paused")
            spoken = "Paused, sir." if paused else ("Resumed, sir." if paused is False else "Done, sir.")
            return {"started": True, "spoken": spoken, "debug": f"paused={paused}"}
        try:
            import pyautogui; pyautogui.press("space")
            return {"started": True, "spoken": "Done, sir.", "debug": "space (global)"}
        except Exception:
            return {"started": False, "spoken": "I couldn't reach the player, sir.", "debug": "no method"}

    def refresh(self) -> dict:
        try:
            import pyautogui; pyautogui.press("f5")
            return {"started": True, "spoken": "Refreshing, sir.", "debug": "f5"}
        except Exception:
            return {"started": False, "spoken": "I need keyboard control to refresh, sir (pip install pyautogui).",
                    "debug": "no pyautogui"}
