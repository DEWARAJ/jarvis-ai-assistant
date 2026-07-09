"""Phase 5 — query effort router. Decides, BEFORE answering, how much machinery a
question deserves and whether it needs the live internet at all.

Three lanes (audit-aligned):
  LANE 1 DIRECT  — math, code logic, reasoning about the user's own files/code/data,
                   definitions, stored memory, JARVIS's own state. NO web search.
  LANE 2 LIVE    — time-sensitive / factual-current: prices, news, weather, "latest",
                   today's data. Fetch live, answer with source + timestamp.
  LANE 3 DEEP    — high-stakes / consequential / ambiguous: "should I", strategy,
                   trading approach, architecture choices. Triggers the multi-agent
                   verification debate.

The differentiation rule (STEP 2): DEFAULT TO NOT SEARCHING. Only Lane 2/Lane-3-live
hits the web. "Always search" degrades answers that depend on the user's own context.

Heuristic + zero-cost so it never consumes an LLM call (keeps the agentic path's
behaviour intact); an LLM refinement hook is provided but optional.
"""
from __future__ import annotations

DIRECT = "DIRECT"   # Lane 1
LIVE = "LIVE"       # Lane 2
DEEP = "DEEP"       # Lane 3

# Lane 3 — consequential / judgement calls. Being wrong here is expensive.
_DEEP_SIGNALS = (
    "should i", "should we", "is it worth", "worth it", "switch my", "switch to",
    "which is better for my", "better strategy", "change my strategy", "trading strategy",
    "all in", "bet on", "quit my", "invest in", "should i invest", "go all in",
    "is it a good idea", "pros and cons of switching", "make the call", "decide between",
    "what's the smartest", "biggest risk",
)
# Lane 2 — time-sensitive / factual-current. Needs the live web.
_LIVE_SIGNALS = (
    "latest", "today", "right now", "current price", "price of", "stock price",
    "this week", "this morning", "breaking", "news", "headlines", "weather",
    "as of", "trending", "who won", "score", "release date", "just announced",
    "what happened", "currently",
)
# Lane 1 — strongly anchored to the user's own context; searching pollutes these.
_DIRECT_SIGNALS = (
    "my code", "my file", "my project", "this function", "my trading bot", "my bot",
    "explain how my", "in my", "the code i", "remember", "what did i", "you said",
    "calculate", "convert", "summarize this", "refactor", "debug this",
)


def route(text: str) -> tuple[str, str]:
    """Return (lane, one-line reason). Pure heuristic; defaults to DIRECT (no search)."""
    low = (text or "").lower().strip()
    if not low:
        return (DIRECT, "Empty input — nothing to look up.")
    if any(s in low for s in _DEEP_SIGNALS):
        return (DEEP, "Consequential judgement call — escalating to multi-agent verification.")
    # own-context wins over a stray live word ("explain how my bot uses the latest price")
    own_ctx = any(s in low for s in _DIRECT_SIGNALS)
    live = any(s in low for s in _LIVE_SIGNALS)
    if live and not own_ctx:
        return (LIVE, "Time-sensitive / factual-current — live lookup with source + timestamp.")
    if own_ctx:
        return (DIRECT, "Anchored to your own context — answering directly, no web search.")
    return (DIRECT, "No time-sensitive or high-stakes signal — answering directly, no web search.")


def needs_search(text: str) -> bool:
    return route(text)[0] in (LIVE, DEEP)


def is_deep(text: str) -> bool:
    return route(text)[0] == DEEP
