"""LLM client for JARVIS — pure standard library (urllib), no pip dependencies.

Switchable "brains" via named profiles in config/settings.json -> llm.profiles:
  - ollama     : local, free, private (provider "ollama")
  - perplexity : cloud, OpenAI-compatible, LIVE WEB SEARCH built in (provider "openai")
  - claude     : cloud, Anthropic Messages API, best reasoning (provider "anthropic")
  - nvidia     : cloud, OpenAI-compatible free tier (provider "openai")

Rules: never stores keys (reads from an env var named in the profile); never crashes
(any failure -> None so callers fall back); generates TEXT only (no actions).
"""
from __future__ import annotations
import os, json, time, urllib.request, urllib.error


class LLMClient:
    def __init__(self, cfg: dict | None = None, logger=None):
        self.full = cfg or {}
        self.logger = logger
        self.enabled = bool(self.full.get("enabled", False))
        self.timeout = int(self.full.get("timeout", 90))
        self.temperature = float(self.full.get("temperature", 0.6))
        self.max_tokens = int(self.full.get("max_tokens", 800))
        self._last_error = None
        self._dead = {}
        self._cooldown = int(self.full.get("fallback_cooldown", 60))
        self.last_brain = None
        self.last_failover = False
        self._cache_on = bool(self.full.get("cache", True))
        self._cache_ttl = int(self.full.get("cache_ttl", 300))
        self._cache_max = int(self.full.get("cache_max", 200))
        self._cache = {}
        self.cache_hits = 0
        self.pinned = False  # True once master says 'use <brain>'; disables smart routing
        self._apply_profile(self.full.get("active"))

    # ---- profile handling ----
    def _apply_profile(self, name):
        profiles = self.full.get("profiles") or {}
        if profiles:
            self.active = name or next(iter(profiles))
            prof = profiles.get(self.active, {})
        else:  # backward-compatible flat config
            self.active = "default"
            prof = self.full
        self.provider = prof.get("provider", "ollama")
        self.model = prof.get("model", "llama3.1:8b")
        self.base_url = prof.get("base_url", "http://localhost:11434").rstrip("/")
        self.api_key_env = prof.get("api_key_env", "")

    def profiles(self) -> list:
        return list((self.full.get("profiles") or {}).keys())

    def switch(self, name: str) -> bool:
        if name in (self.full.get("profiles") or {}):
            self._apply_profile(name)
            self.pinned = True  # manual 'use <brain>' overrides smart auto-routing
            return True
        return False

    def auto(self) -> None:
        """Release a manual pin and return to smart per-task routing."""
        self.pinned = False

    @property
    def available(self) -> bool:
        return self.enabled

    def _key_ok(self) -> bool:
        return (not self.api_key_env) or bool(os.environ.get(self.api_key_env))

    def status(self) -> str:
        if not self.enabled:
            return "LLM: disabled (set llm.enabled=true in config/settings.json)"
        key = "ok" if self._key_ok() else f"MISSING env {self.api_key_env}"
        opts = ("/".join(self.profiles())) if self.profiles() else "flat"
        return f"LLM: [{self.active}] {self.provider} · model={self.model} · key={key} · profiles: {opts}"

    # ---- smart per-task brain routing ----
    # Pick the best brain for the *kind* of task, so JARVIS flexibly changes model per request.
    # Heuristic, zero-cost, overridable. Only reorders among brains that have usable keys.
    _ROUTE_RULES = (
        # (task class, profile preference order, trigger substrings)
        ("research", ("perplexity", "gemini", "claude"),
         ("latest", "news", "current", "today", "right now", "price of", "stock", "who is",
          "what happened", "search the web", "look up", "weather", "score", "release date",
          "recent", "as of", "this week", "trending", "live")),
        ("reasoning", ("claude", "gemini", "nvidia"),
         ("why", "explain", "analyze", "analyse", "architecture", "design", "strategy",
          "debug", "refactor", "plan ", "trade-off", "tradeoff", "prove", "step by step",
          "complex", "reason", "compare", "pros and cons", "decide", "evaluate")),
        ("code", ("claude", "nvidia", "gemini"),
         ("code", "function", "python", "javascript", "bug", "stack trace", "regex",
          "sql", "api", "class ", "compile", "error:", "exception", "script")),
        ("quick", ("gemini", "nvidia", "perplexity"),
         ("summarize", "summarise", "translate", "rephrase", "shorten", "tldr",
          "quick", "one line", "yes or no", "format", "list ")),
    )

    # ---- complexity scorer (1-10) — v3.0 routing enhancement ----
    _COMPLEXITY_HIGH = (
        "trade", "trading", "invest", "portfolio", "risk", "hedge", "options",
        "backtest", "strategy", "deploy", "architecture", "orchestrate", "mission",
        "legal", "contract", "irreversible", "delete", "security", "permission",
        "multi-step", "multi-phase", "refactor", "redesign",
        "self-modify", "self-upgrade", "class b", "class c", "class x",
    )
    _COMPLEXITY_MED = (
        "code", "function", "algorithm", "explain", "analyze", "analyse",
        "compare", "design", "plan", "summarize", "research", "build",
        "debug", "error", "exception", "api", "database",
    )
    _COMPLEXITY_LOW = (
        "what is", "who is", "when", "where", "yes or no", "translate",
        "rephrase", "format", "list", "quick", "tldr", "shorten",
    )

    def complexity_score(self, text: str) -> int:
        """Return task complexity 1-10.
        1-3: simple lookup / format. 4-6: coding/analysis. 7-9: multi-step/financial. 10: critical/Class-B+.
        """
        t = text.lower()
        score = 5
        low_hits  = sum(1 for k in self._COMPLEXITY_LOW  if k in t)
        med_hits  = sum(1 for k in self._COMPLEXITY_MED  if k in t)
        high_hits = sum(1 for k in self._COMPLEXITY_HIGH if k in t)
        score -= min(low_hits * 2, 4)
        score += min(med_hits, 3)
        score += min(high_hits * 2, 5)
        words = len(t.split())
        if words > 100: score += 1
        if words > 250: score += 1
        return max(1, min(10, score))

    def _route_brain(self, system: str, user: str) -> str | None:
        """Return the profile name best suited to this request, or None to keep default order.

        Framework §8 (Model Routing by Task Complexity): complexity_score() drives escalation.
        Score 8+ → frontier brain. Score ≤3 → fast/cheap. 4–7 → keyword rules."""
        if self.pinned or self.full.get("local_only") or not self.full.get("smart_route", True):
            return None
        text = f"{system}\n{user}".lower()
        score = self.complexity_score(text)
        self.last_complexity = score

        if score >= 8 or any(t in text for t in self._FRONTIER_TRIGGERS):
            for name in self.full.get("frontier_order") or ("claude", "gemini", "nvidia"):
                if self._profile_usable(name) and not self._is_dead(name):
                    return name
        if score <= 3:
            for name in self.full.get("fast_order") or ("gemini", "nvidia", "ollama"):
                if self._profile_usable(name) and not self._is_dead(name):
                    return name
        for _cls, prefs, triggers in self._ROUTE_RULES:
            if any(t in text for t in triggers):
                for name in prefs:
                    if self._profile_usable(name) and not self._is_dead(name):
                        return name
        return None

    # High-stakes signals that demand the frontier/high-reasoning brain (§8).
    _FRONTIER_TRIGGERS = (
        "class b", "self-upgrade", "self upgrade", "modify your own", "rewrite your",
        "trade", "trading", "invest", "portfolio", "position size", "risk reward",
        "risk:reward", "r:r", "backtest", "hedge", "options", "derivatives", "valuation",
        "financial decision", "legal", "contract", "irreversible", "delete everything",
        "wire transfer", "large purchase", "security setting", "permission change",
        "multi-step", "orchestrate", "high-stakes", "high stakes", "mission critical",
    )

    # ---- main entry ----
    def chat(self, system: str, user: str, history: list | None = None, no_cache: bool = False) -> str | None:
        """Resilient chat: route to the best brain for THIS task, then automatically fail over
        through the other usable brains (cloud first, local Ollama as the floor) so JARVIS never
        goes dumb. Records which brain actually answered in self.last_brain / self.last_failover.
        Dead brains are skipped for a short cooldown so we don't keep retrying a known-down one."""
        if not self.enabled:
            return None
        convo = list(history[-10:]) if history else []
        convo.append({"role": "user", "content": user})
        # BUG 10: live-data synthesis (price/news/web search) bypasses the cache so a
        # 300s-stale answer is never served as current.
        ck = self._cache_key(system, user, history) if (self._cache_on and not no_cache) else None
        if ck:
            hit = self._cache_get(ck)
            if hit is not None:
                self.cache_hits += 1
                self.last_brain = "cache"
                self.last_failover = False
                return hit
        order = self._fallback_order()
        routed = self._route_brain(system, user)
        if routed and routed in order:
            order.remove(routed)
            order.insert(0, routed)  # try the task-matched brain first
        self.last_brain = None
        self.last_failover = False
        saved = (self.active, self.provider, self.model, self.base_url, self.api_key_env)
        try:
            for name in order:
                if self._is_dead(name):
                    continue
                self._apply_named(name)
                out = self._call_provider(system, convo)
                if out:
                    self.last_brain = name
                    self.last_failover = (name != saved[0])
                    self._mark_alive(name)
                    if self.last_failover and self.logger:
                        self.logger.warn(f"LLM failover: {saved[0]} -> {name}")
                    if ck:
                        self._cache_put(ck, out)
                    return out
                self._mark_dead(name)
            return None
        finally:
            self.active, self.provider, self.model, self.base_url, self.api_key_env = saved

    def _call_provider(self, system, convo) -> str | None:
        try:
            if self.provider == "ollama":
                return self._ollama(system, convo)
            if self.provider == "anthropic":
                return self._anthropic(system, convo)
            return self._openai_compatible(system, convo)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError, KeyError) as e:
            self._last_error = str(e)
            if self.logger:
                self.logger.warn(f"LLM call failed ({self.active}/{self.provider}): {e}")
            return None

    def _apply_named(self, name):
        prof = (self.full.get("profiles") or {}).get(name, {})
        if prof:
            self.provider = prof.get("provider", "ollama")
            self.model = prof.get("model", "llama3.1:8b")
            self.base_url = prof.get("base_url", "http://localhost:11434").rstrip("/")
            self.api_key_env = prof.get("api_key_env", "")

    def _profile_usable(self, name) -> bool:
        prof = (self.full.get("profiles") or {}).get(name)
        if not prof:
            return False
        env = prof.get("api_key_env", "")
        return (not env) or bool(os.environ.get(env))

    def _fallback_order(self) -> list:
        profiles = self.full.get("profiles") or {}
        if not profiles:
            return ["default"]
        if self.full.get("local_only"):
            local = [n for n in profiles if profiles[n].get("provider") == "ollama"]
            return local or ["ollama"]
        order = []
        if self._profile_usable(self.active):
            order.append(self.active)
        for n in (self.full.get("fallback") or []):
            if n not in order and self._profile_usable(n):
                order.append(n)
        rest = [n for n in profiles if n not in order and self._profile_usable(n)]
        rest.sort(key=lambda n: profiles[n].get("provider") == "ollama")  # ollama last = local floor
        order.extend(rest)
        return order

    def _is_dead(self, name) -> bool:
        return time.time() < self._dead.get(name, 0)

    def _mark_dead(self, name):
        self._dead[name] = time.time() + self._cooldown

    def _mark_alive(self, name):
        self._dead.pop(name, None)

    # ---- response cache (token efficiency for agent loops) ----
    def _cache_key(self, system, user, history):
        import hashlib, json as _j
        h = _j.dumps(history[-10:], sort_keys=True) if history else ""
        raw = (self.active or "") + "|" + (self.model or "") + "|" + system + "|" + user + "|" + h
        return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()

    def _cache_get(self, key):
        import time
        v = self._cache.get(key)
        if not v:
            return None
        ts, val = v
        if time.time() - ts > self._cache_ttl:
            self._cache.pop(key, None)
            return None
        return val

    def _cache_put(self, key, val):
        import time
        if len(self._cache) >= self._cache_max:
            oldest = min(self._cache.items(), key=lambda kv: kv[1][0])[0]
            self._cache.pop(oldest, None)
        self._cache[key] = (time.time(), val)

    def clear_cache(self) -> int:
        n = len(self._cache)
        self._cache = {}
        return n

    def brain_health(self) -> list:
        """Per-profile health for doctor/status."""
        profiles = self.full.get("profiles") or {}
        return [{"name": n, "usable": self._profile_usable(n), "cooldown": self._is_dead(n),
                 "provider": profiles.get(n, {}).get("provider", "")} for n in self.profiles()]

    def vision(self, system: str, user_text: str, image_b64: str, media_type: str = "image/png") -> str | None:
        """Send a screenshot to a vision model and return its description. Anthropic (Claude) only.
        Uses the active brain if it's anthropic, else falls back to ANTHROPIC_API_KEY if present."""
        import os
        provider, base_url, model, key_env = self.provider, self.base_url, self.model, self.api_key_env
        if provider != "anthropic":
            # try the claude profile from the full config
            prof = (self.full.get("profiles") or {}).get("claude")
            if prof and os.environ.get(prof.get("api_key_env", "")):
                provider, base_url, model, key_env = "anthropic", prof["base_url"].rstrip("/"), prof["model"], prof["api_key_env"]
            else:
                return None
        key = os.environ.get(key_env) if key_env else None
        if not key:
            return None
        url = f"{base_url}/v1/messages"
        headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01", "x-api-key": key}
        payload = {"model": model, "max_tokens": self.max_tokens, "system": system,
                   "messages": [{"role": "user", "content": [
                       {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                       {"type": "text", "text": user_text}]}]}
        try:
            body = self._post(url, payload, headers)
            blocks = body.get("content") or []
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
            return text or None
        except urllib.error.HTTPError as e:
            # Capture Anthropic's actual error message (the response body), not just the code —
            # so "vision request didn't come back" becomes a real diagnostic (bad model, oversized
            # image, invalid key, etc.).
            try:
                detail = e.read().decode("utf-8", "ignore")[:300]
            except Exception:
                detail = ""
            self._last_error = f"vision HTTP {e.code}: {detail or getattr(e, 'reason', '')}"
            if self.logger:
                self.logger.warn(self._last_error)
            return None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as e:
            self._last_error = f"vision: {e}"
            return None

    def reachable(self) -> bool:
        if not self.enabled:
            return False
        return bool(self.chat("You are a healthcheck.", "Reply with the single word OK."))

    # ---- providers ----
    def _post(self, url: str, payload: dict, headers: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _ollama(self, system, convo) -> str | None:
        url = f"{self.base_url}/api/chat"
        messages = [{"role": "system", "content": system}] + convo
        payload = {"model": self.model, "messages": messages, "stream": False,
                   "options": {"temperature": self.temperature, "num_predict": self.max_tokens}}
        body = self._post(url, payload, {"Content-Type": "application/json"})
        return (body.get("message") or {}).get("content", "").strip() or None

    def _openai_compatible(self, system, convo) -> str | None:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key_env:
            key = os.environ.get(self.api_key_env)
            if not key:
                self._last_error = f"missing env {self.api_key_env}"
                return None
            headers["Authorization"] = f"Bearer {key}"
        messages = [{"role": "system", "content": system}] + convo
        payload = {"model": self.model, "messages": messages,
                   "temperature": self.temperature, "max_tokens": self.max_tokens, "stream": False}
        body = self._post(url, payload, headers)
        choices = body.get("choices") or []
        if not choices:
            return None
        return (choices[0].get("message") or {}).get("content", "").strip() or None

    def _anthropic(self, system, convo) -> str | None:
        url = f"{self.base_url}/v1/messages"
        key = os.environ.get(self.api_key_env) if self.api_key_env else None
        if self.api_key_env and not key:
            self._last_error = f"missing env {self.api_key_env}"
            return None
        headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
        if key:
            headers["x-api-key"] = key
        payload = {"model": self.model, "max_tokens": self.max_tokens,
                   "system": system, "messages": convo}
        body = self._post(url, payload, headers)
        blocks = body.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        return text or None
