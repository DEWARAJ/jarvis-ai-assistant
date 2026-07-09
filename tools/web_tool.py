"""Web access for JARVIS — fetch & clean any page (pure standard library)."""
from __future__ import annotations
import re, urllib.request, urllib.error
from datetime import datetime, timezone
from html import unescape
from tools.base_tool import BaseTool

_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WS = re.compile(r"[ \t\r\f]+")
_NL = re.compile(r"\n{3,}")


class WebTool(BaseTool):
    name = "web"; scope = "read public web pages"

    def fetch(self, url: str, max_chars: int = 9000) -> tuple[str, str]:
        """Return (status, text). text empty on failure."""
        url = (url or "").strip().strip('"').strip("'")
        if not url:
            return ("Give me a URL, e.g. 'read url https://example.com'.", "")
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (JARVIS-OS research agent)",
                "Accept": "text/html,application/xhtml+xml",
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                ctype = resp.headers.get("Content-Type", "")
                raw = resp.read(2_500_000)
            charset = "utf-8"
            if "charset=" in ctype:
                charset = ctype.split("charset=")[-1].split(";")[0].strip() or "utf-8"
            html = raw.decode(charset, errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as e:
            return (f"I couldn't reach that page ({e}).", "")
        # crude title
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = unescape(_TAG.sub("", m.group(1)).strip()) if m else url
        body = _SCRIPT.sub(" ", html)
        text = unescape(_TAG.sub(" ", body))
        text = _WS.sub(" ", text)
        text = _NL.sub("\n\n", "\n".join(line.strip() for line in text.splitlines()))
        text = text.strip()[:max_chars]
        if not text:
            return (f"Loaded {url} but found no readable text (it may be a JavaScript-only page).", "")
        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return (f"Fetched: {title}", f"URL: {url}\nTITLE: {title}\nFETCHED: {fetched_at}\n\n{text}")

    def search(self, query: str, n: int = 5) -> tuple[str, str]:
        """Web search — Perplexity LLM primary (if key set), Bing HTML second, DuckDuckGo fallback."""
        import urllib.parse
        q = (query or "").strip()
        if not q:
            return ("What should I search for?", "")
        searched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # ---- engine 0: Perplexity (search-native LLM, most reliable, no scraping) ----
        try:
            llm = (self.context or {}).get("llm") if isinstance(self.context, dict) else None
            if llm and getattr(llm, "available", False):
                import os
                perp_key = os.getenv("PERPLEXITY_API_KEY", "")
                if perp_key:
                    # Pin to perplexity for this call only (don't change global active brain)
                    from core.llm_client import LLMClient
                    cfg = {"enabled": True, "active": "perplexity", "timeout": 30, "max_tokens": 600,
                           "profiles": {"perplexity": {
                               "provider": "openai", "model": "sonar-pro",
                               "base_url": "https://api.perplexity.ai",
                               "api_key_env": "PERPLEXITY_API_KEY"}}}
                    plx = LLMClient(cfg, self.logger)
                    if plx.available:
                        prompt = (f"Search the web for: {q}\n\n"
                                  f"Return the top {n} results as a plain numbered list: "
                                  "title, one-sentence summary, and source URL. "
                                  "No preamble, no markdown fences.")
                        result = plx.chat("You are a web search assistant. Return factual, source-cited results only.", prompt)
                        if result and len(result) > 40:
                            return (f"Top results for: {q} (via Perplexity, {searched_at})",
                                    f"SEARCHED: {searched_at} (Perplexity)\n\n{result.strip()}")
        except Exception:
            pass

        # ---- engine 1: Bing HTML (more permissive bot policy than DDG) ----
        bing_url = "https://www.bing.com/search?q=" + urllib.parse.quote(q) + "&setlang=en"
        try:
            req = urllib.request.Request(bing_url, headers={
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/124.0 Safari/537.36"),
                "Accept-Language": "en-US,en;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=20) as r:
                html = r.read().decode("utf-8", errors="replace")
            items = []
            # Bing result titles sit in <h2><a href="...">...</a></h2>
            for m in re.finditer(r'<h2[^>]*>\s*<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
                url_r = unescape(m.group(1))
                title = unescape(_TAG.sub("", m.group(2))).strip()
                if title and "bing.com" not in url_r:
                    items.append((title, url_r, ""))
                if len(items) >= n:
                    break
            if items:
                lines = [f"{i+1}. {t}\n   {l}" for i, (t, l, _) in enumerate(items)]
                return (f"Top {len(items)} Bing results for: {q}",
                        f"SEARCHED: {searched_at} (Bing)\n\n" + "\n".join(lines))
        except Exception:
            pass

        # ---- engine 2: DuckDuckGo HTML fallback ----
        ddg_url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
        try:
            req = urllib.request.Request(ddg_url, headers={"User-Agent": "Mozilla/5.0 (JARVIS research)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                html = r.read().decode("utf-8", errors="replace")
            items = []
            for m in re.finditer(r'result__a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
                link = unescape(m.group(1)); title = unescape(_TAG.sub("", m.group(2))).strip()
                mu = re.search(r"uddg=([^&]+)", link)
                if mu:
                    link = urllib.parse.unquote(mu.group(1))
                if title:
                    items.append((title, link))
                if len(items) >= n:
                    break
            snips = [unescape(_TAG.sub("", x)).strip()
                     for x in re.findall(r'result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)]
            if items:
                lines = []
                for i, (t, l) in enumerate(items):
                    sn = snips[i] if i < len(snips) else ""
                    lines.append(f"{i+1}. {t}\n   {sn}\n   {l}")
                return (f"Top {len(items)} results for: {q}",
                        f"SEARCHED: {searched_at} (DDG)\n\n" + "\n".join(lines))
        except Exception:
            pass

        return (f"Web search unavailable right now, sir — both Bing and DuckDuckGo failed for: {q}", "")
