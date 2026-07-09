"""JARVIS v6.0 — Multi-LLM router with complexity scoring and health cache."""
from __future__ import annotations
import os, time
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class LLMResponse:
    text: str
    model: str
    complexity: int
    elapsed: float
    error: Optional[str] = None

_HEALTH: dict[str, float] = {}  # model → last_ok timestamp
_HEALTH_TTL = 300  # 5 min

_FRONTIER_TRIGGERS = ("strategy","architecture","mission critical","trading system",
                      "full analysis","deep research","ooda","independent thinking",
                      "build complete","comprehensive","step by step")
_FAST_TRIGGERS     = ("what is","define","translate","simple","quick","yes or no",
                      "single word","one sentence","summarize briefly")
_WEB_TRIGGERS      = ("search","latest","news","current","today","price","weather",
                      "online","look up","fetch","browse","recent")
_CODE_TRIGGERS     = ("write code","implement","function","class","script","fix bug",
                      "refactor","debug","test","module")

def complexity_score(text: str) -> int:
    t = (text or "").lower()
    score = 5
    words = len(t.split())
    if words > 80:  score += 2
    elif words > 40: score += 1
    elif words < 8:  score -= 2
    if any(k in t for k in _FRONTIER_TRIGGERS): score += 3
    if any(k in t for k in _FAST_TRIGGERS):     score -= 2
    if any(k in t for k in _CODE_TRIGGERS):     score += 1
    return max(1, min(10, score))

def classify_task(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in _WEB_TRIGGERS):   return "web_research"
    if any(k in t for k in _CODE_TRIGGERS):  return "code_generation"
    if "trade" in t or "alpaca" in t:        return "trading"
    if "email" in t or "calendar" in t:     return "communication"
    if "file" in t or "document" in t:      return "file_ops"
    return "general"

def route(text: str) -> str:
    score = complexity_score(text)
    if score >= 8: return "claude-sonnet-4-6"     # frontier
    if score <= 3: return "claude-haiku-4-5-20251001"  # fast
    # 4-7: keyword rules
    t = text.lower()
    if any(k in t for k in _FRONTIER_TRIGGERS): return "claude-sonnet-4-6"
    return "claude-sonnet-4-6"  # default balanced

def call(text: str, system: str = "", history: list | None = None,
         model: str | None = None, max_tokens: int = 4096) -> LLMResponse:
    import anthropic
    key = os.getenv("ANTHROPIC_API_KEY","")
    if not key:
        return LLMResponse("ANTHROPIC_API_KEY not set.", "none", 0, 0,
                           error="missing_key")
    selected = model or route(text)
    score    = complexity_score(text)
    msgs     = list(history or []) + [{"role":"user","content":text}]
    t0 = time.time()
    try:
        client = anthropic.Anthropic(api_key=key)
        r = client.messages.create(
            model=selected, max_tokens=max_tokens,
            system=system or "You are JARVIS, Dew's autonomous AI agent.",
            messages=msgs)
        return LLMResponse(r.content[0].text, selected, score,
                           round(time.time()-t0, 2))
    except Exception as e:
        return LLMResponse(f"[LLM error: {e}]", selected, score,
                           round(time.time()-t0, 2), error=str(e))

def health_report() -> str:
    models = ["claude-sonnet-4-6","claude-haiku-4-5-20251001"]
    key = os.getenv("ANTHROPIC_API_KEY","")
    if not key: return "ANTHROPIC_API_KEY not set."
    lines = ["LLM Health:"]
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        for m in models:
            t0 = time.time()
            try:
                r = client.messages.create(model=m, max_tokens=5,
                    messages=[{"role":"user","content":"hi"}])
                lines.append(f"  {m}: OK ({time.time()-t0:.1f}s)")
            except Exception as e:
                lines.append(f"  {m}: FAIL — {e}")
    except ImportError:
        lines.append("  anthropic not installed")
    return "\n".join(lines)
