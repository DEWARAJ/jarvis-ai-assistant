"""
internet_layer.py  —  JARVIS v7.0
Live internet integration. Auto-triggers search before Claude reasons on
time-sensitive queries. Never answers stale from training memory.

Search priority:
  1. Firecrawl  (key: FIRECRAWL_API_KEY  — deep content extraction)
  2. Brave      (key: BRAVE_SEARCH_API_KEY — fast JSON results)
  3. Perplexity (key: PERPLEXITY_API_KEY  — already set in .env)
  4. Tavily     (key: TAVILY_API_KEY      — research-optimised)
  5. DuckDuckGo (no key — always available fallback)
"""
from __future__ import annotations
import os, re
from datetime import datetime

try:
    import requests as _req; _REQ_OK = True
except ImportError:
    _req = None; _REQ_OK = False

try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

# ── Auto-trigger patterns ─────────────────────────────────────────────────────
_TIME_PATTERNS = [
    r"\bprice\b", r"\bcost\b", r"\bworth\b", r"\bstock\b", r"\bcrypto\b",
    r"\bbitcoin\b", r"\beth\b", r"\bnews\b", r"\blatest\b", r"\bcurrent\b",
    r"\btoday\b", r"\bnow\b", r"\btonight\b", r"\bthis week\b",
    r"\bweather\b", r"\btemperature\b", r"\bforecast\b",
    r"\bwho is\b", r"\bwhat is happening\b", r"\bwhat happened\b",
    r"\bwhen did\b", r"\bhow much is\b",
    r"\bresults\b", r"\bscore\b", r"\bwinner\b", r"\belection\b",
    r"\bmarket\b", r"\bbreaking\b", r"\blive\b",
]
_COMPILED = [re.compile(p, re.I) for p in _TIME_PATTERNS]


def needs_live_search(query: str) -> bool:
    return any(p.search(query) for p in _COMPILED)


# ── Provider: Firecrawl ───────────────────────────────────────────────────────
def firecrawl_search(query: str, count: int = 5) -> list[dict]:
    key = os.getenv("FIRECRAWL_API_KEY", "")
    if not key or not _REQ_OK:
        return []
    try:
        r = _req.post(
            "https://api.firecrawl.dev/v1/search",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"query": query, "limit": count,
                  "scrapeOptions": {"formats": ["markdown"]}},
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("data", [])
        out = []
        for x in results[:count]:
            snippet = x.get("markdown", x.get("description", ""))[:300]
            out.append({"title": x.get("title", ""),
                        "url": x.get("url", ""),
                        "snippet": snippet})
        return out
    except Exception:
        return []


def firecrawl_scrape(url: str) -> str:
    """Scrape a single URL via Firecrawl for deep content extraction."""
    key = os.getenv("FIRECRAWL_API_KEY", "")
    if not key or not _REQ_OK:
        return "[Firecrawl] FIRECRAWL_API_KEY not set."
    try:
        r = _req.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"url": url, "formats": ["markdown"],
                  "onlyMainContent": True},
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("data", {}).get("markdown", "")[:6000]
    except Exception as e:
        return f"[Firecrawl scrape error] {e}"


# ── Provider: Brave ───────────────────────────────────────────────────────────
def brave_search(query: str, count: int = 5) -> list[dict]:
    key = os.getenv("BRAVE_SEARCH_API_KEY", "")
    if not key or not _REQ_OK:
        return []
    try:
        r = _req.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json",
                     "X-Subscription-Token": key},
            params={"q": query, "count": count},
            timeout=8,
        )
        r.raise_for_status()
        results = r.json().get("web", {}).get("results", [])
        return [{"title": x.get("title", ""), "url": x.get("url", ""),
                 "snippet": x.get("description", "")} for x in results]
    except Exception:
        return []


# ── Provider: Perplexity ──────────────────────────────────────────────────────
def perplexity_search(query: str) -> list[dict]:
    key = os.getenv("PERPLEXITY_API_KEY", "")
    if not key or not _REQ_OK:
        return []
    try:
        r = _req.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"model": "sonar",
                  "messages": [{"role": "user", "content": query}],
                  "max_tokens": 512},
            timeout=12,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return [{"title": "Perplexity Answer", "url": "perplexity",
                 "snippet": content[:800]}]
    except Exception:
        return []


# ── Provider: Tavily ──────────────────────────────────────────────────────────
def tavily_search(query: str, count: int = 5) -> list[dict]:
    key = os.getenv("TAVILY_API_KEY", "")
    if not key or not _REQ_OK:
        return []
    try:
        r = _req.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": query, "max_results": count,
                  "search_depth": "basic", "include_answer": True},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        out = [{"title": x.get("title", ""), "url": x.get("url", ""),
                "snippet": x.get("content", "")}
               for x in data.get("results", [])]
        if data.get("answer"):
            out.insert(0, {"title": "Direct Answer", "url": "tavily",
                           "snippet": data["answer"]})
        return out
    except Exception:
        return []


# ── Provider: DuckDuckGo ──────────────────────────────────────────────────────
def ddg_search(query: str) -> list[dict]:
    if not _REQ_OK:
        return []
    try:
        r = _req.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json",
                    "no_html": 1, "skip_disambig": 1},
            timeout=6,
        )
        data = r.json()
        out = []
        if data.get("AbstractText"):
            out.append({"title": data.get("Heading", ""),
                        "url": data.get("AbstractURL", ""),
                        "snippet": data["AbstractText"]})
        for t in data.get("RelatedTopics", [])[:3]:
            if isinstance(t, dict) and t.get("Text"):
                out.append({"title": t["Text"][:60],
                            "url": t.get("FirstURL", ""),
                            "snippet": t["Text"]})
        return out
    except Exception:
        return []


# ── Master search ─────────────────────────────────────────────────────────────
def live_search(query: str, count: int = 5) -> dict:
    """Try all providers in priority order. Return first non-empty result."""
    for provider, fn in [
        ("firecrawl",  lambda: firecrawl_search(query, count)),
        ("brave",      lambda: brave_search(query, count)),
        ("perplexity", lambda: perplexity_search(query)),
        ("tavily",     lambda: tavily_search(query, count)),
        ("duckduckgo", lambda: ddg_search(query)),
    ]:
        results = fn()
        if results:
            return {"results": results, "source": provider,
                    "query": query, "timestamp": datetime.now().isoformat()}
    return {"results": [], "source": "none",
            "query": query, "timestamp": datetime.now().isoformat()}


def format_search_for_context(data: dict) -> str:
    if not data.get("results"):
        return ""
    lines = [
        f"[LIVE SEARCH — {data['source'].upper()} — {data['timestamp'][:16]}]",
        f"Query: {data['query']}", ""
    ]
    for i, r in enumerate(data["results"][:5], 1):
        lines.append(f"{i}. {r.get('title', '')}")
        lines.append(f"   {r.get('snippet', '')[:250]}")
        if r.get("url") and r["url"] not in ("tavily", "perplexity"):
            lines.append(f"   Source: {r['url']}")
        lines.append("")
    lines.append("[END LIVE SEARCH]")
    return "\n".join(lines)


def augment_query_with_live_data(user_query: str) -> str:
    """Prepend live search context if query is time-sensitive."""
    if not needs_live_search(user_query):
        return user_query
    data = live_search(user_query)
    if not data["results"]:
        return user_query
    return f"{format_search_for_context(data)}\n\nUser query: {user_query}"
