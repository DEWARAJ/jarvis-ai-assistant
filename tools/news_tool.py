"""Live news for JARVIS via public RSS feeds (no API key, pure standard library).

Topic-aware: maps 'ai', 'crypto', 'stocks', 'ecommerce', 'business', 'world', 'tech'
to a Google News RSS query (with Yahoo Finance for markets). Returns structured items
(headline, source, link, published). Graceful if the network is unavailable.
"""
from __future__ import annotations
import urllib.request, urllib.error, urllib.parse, re
from html import unescape
from tools.base_tool import BaseTool

TOPIC_QUERY = {
    "ai": "artificial intelligence AI", "tech": "technology", "world": "world news",
    "business": "business", "ecommerce": "ecommerce online retail Shopify",
    "marketing": "digital marketing", "crypto": "cryptocurrency bitcoin",
    "stocks": "stock market", "markets": "stock market", "startup": "startups",
}
GOOGLE_NEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
GOOGLE_TOP = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
YAHOO_FIN = "https://finance.yahoo.com/news/rssindex"


class NewsTool(BaseTool):
    name = "news"; scope = "live news via public RSS"

    def _fetch(self, url: str) -> str | None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (JARVIS news)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
            return None

    @staticmethod
    def _parse(xml: str, limit: int) -> list:
        items = []
        for block in re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)[:limit]:
            def grab(tag):
                m = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.DOTALL)
                if not m:
                    return ""
                v = m.group(1).strip()
                v = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", v, flags=re.DOTALL)
                return unescape(re.sub(r"<[^>]+>", "", v)).strip()
            title = grab("title")
            if not title:
                continue
            src = grab("source") or ""
            # Google News titles end with " - Source"
            if not src and " - " in title:
                title, src = title.rsplit(" - ", 1)
            items.append({"headline": title.strip(), "source": src.strip(),
                          "link": grab("link"), "published": grab("pubDate")})
        return items

    def headlines(self, topic: str = "", limit: int = 6) -> dict:
        topic = (topic or "").strip().lower()
        key = next((k for k in TOPIC_QUERY if k in topic), None)
        if key in ("stocks", "markets"):
            xml = self._fetch(YAHOO_FIN) or self._fetch(GOOGLE_NEWS.format(q=urllib.parse.quote("stock market")))
            label = "markets"
        elif key:
            xml = self._fetch(GOOGLE_NEWS.format(q=urllib.parse.quote(TOPIC_QUERY[key])))
            label = key
        elif topic:
            xml = self._fetch(GOOGLE_NEWS.format(q=urllib.parse.quote(topic)))
            label = topic
        else:
            xml = self._fetch(GOOGLE_TOP)
            label = "top"
        if not xml:
            return {"ok": False, "topic": label, "items": [],
                    "result_message": "Couldn't reach the news feeds right now (network issue)."}
        items = self._parse(xml, limit)
        if not items:
            return {"ok": False, "topic": label, "items": [],
                    "result_message": "Feed reachable but no stories parsed."}
        return {"ok": True, "topic": label, "items": items,
                "result_message": f"{len(items)} {label} headlines."}

    @staticmethod
    def format(items: list) -> str:
        out = []
        for i, it in enumerate(items, 1):
            line = f"{i}. {it['headline']}"
            if it.get("source"):
                line += f"  — {it['source']}"
            if it.get("published"):
                line += f"  [{it['published']}]"
            if it.get("link"):
                line += f"\n   {it['link']}"
            out.append(line)
        return "\n".join(out)
