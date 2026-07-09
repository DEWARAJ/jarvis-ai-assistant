"""Browser control for JARVIS — actually opens real search results / sites on screen.

Primary method: build the engine's search URL and open it in the default browser
(reliable, instant, no heavy deps) — this genuinely shows live results on screen.
Playwright-based deep automation can be layered on later; this is the dependable base.
Returns STRUCTURED feedback so the agent can report honestly.
"""
from __future__ import annotations
import sys, os, webbrowser, urllib.parse
from tools.base_tool import BaseTool

ENGINES = {
    "google": "https://www.google.com/search?q={q}",
    "youtube": "https://www.youtube.com/results?search_query={q}",
    "amazon": "https://www.amazon.com/s?k={q}",
    "maps": "https://www.google.com/maps/search/{q}",
    "bing": "https://www.bing.com/search?q={q}",
    "duckduckgo": "https://duckduckgo.com/?q={q}",
}
HOME = {
    "google": "https://www.google.com", "youtube": "https://www.youtube.com",
    "amazon": "https://www.amazon.com", "maps": "https://www.google.com/maps",
}


class BrowserControlTool(BaseTool):
    name = "browser"; scope = "open sites & search results"

    def _open(self, url: str) -> bool:
        try:
            if sys.platform.startswith("win"):
                import shutil, subprocess
                exe = shutil.which("chrome")
                if not exe:
                    for pth in (r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                                r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                                os.path.expanduser(r"~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")):
                        if os.path.exists(pth):
                            exe = pth; break
                if exe:
                    subprocess.Popen([exe, url]); return True
                subprocess.Popen(f'start chrome "{url}"', shell=True); return True
            else:
                webbrowser.open(url)
            return True
        except Exception:
            try:
                return webbrowser.open(url)
            except Exception:
                return False

    def search(self, engine: str, query: str) -> dict:
        engine = (engine or "google").lower()
        q = (query or "").strip()
        tmpl = ENGINES.get(engine, ENGINES["google"])
        if not q:
            url = HOME.get(engine, "https://www.google.com")
        else:
            url = tmpl.format(q=urllib.parse.quote_plus(q))
        started = self._open(url)
        return {
            "action": "browser_search", "engine": engine, "query": q, "url": url,
            "started": started, "completed": started,
            "result_message": (f"Opened {engine.title()} "
                               + (f"results for “{q}”." if q else "homepage.")) if started
                              else f"Couldn't open the browser for {engine}.",
            "error_message": "" if started else "webbrowser/os.startfile failed",
            "next_step": "Results are loading in your browser." if started
                         else "Open your browser manually and try again.",
        }

    def open_url(self, url: str) -> dict:
        url = (url or "").strip().strip('"').strip("'")
        if url and not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        if not url:
            return {"action": "open_url", "url": "", "started": False, "completed": False,
                    "result_message": "No URL given.", "error_message": "empty url",
                    "next_step": "Give me a web address, e.g. open website example.com"}
        started = self._open(url)
        return {"action": "open_url", "url": url, "started": started, "completed": started,
                "result_message": f"Opening {url}." if started else f"Couldn't open {url}.",
                "error_message": "" if started else "browser open failed",
                "next_step": "The page is loading in your browser." if started else "Try opening it manually."}
