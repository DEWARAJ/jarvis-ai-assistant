"""Trading RESEARCH tool for JARVIS — live prices, watchlist, journal, risk math.

Research only. NEVER places trades, connects a broker, or guarantees profit.
Live data uses free, keyless sources:
  - Crypto: CoinGecko  (https://api.coingecko.com)
  - Stocks: Stooq CSV   (https://stooq.com)
Pure standard library; graceful on any network failure.
"""
from __future__ import annotations
import os, json, csv, io, urllib.request, urllib.error
from datetime import datetime
from tools.base_tool import BaseTool

# common crypto aliases -> CoinGecko ids
CRYPTO = {
    "btc": "bitcoin", "bitcoin": "bitcoin", "eth": "ethereum", "ethereum": "ethereum",
    "sol": "solana", "solana": "solana", "xrp": "ripple", "ripple": "ripple",
    "ada": "cardano", "cardano": "cardano", "doge": "dogecoin", "dogecoin": "dogecoin",
    "bnb": "binancecoin", "matic": "matic-network", "dot": "polkadot", "ltc": "litecoin",
    "link": "chainlink", "avax": "avalanche-2", "trx": "tron", "shib": "shiba-inu",
}


class TradingTool(BaseTool):
    name = "trading"; scope = "research: live prices, watchlist, journal, risk"

    def __init__(self, context=None, logger=None):
        super().__init__(context, logger)
        os.makedirs("memory", exist_ok=True)
        self.journal_path = os.path.join("memory", "trading_journal.json")
        self.watch_path = os.path.join("memory", "watchlist.json")

    # ---- persistence ----
    def _load(self, path, default):
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return default
        return default

    def _save(self, path, data) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except OSError:
            return False

    # ---- live prices ----
    def _get(self, url: str, timeout=15) -> str | None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-OS/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as e:
            self._err = str(e)
            return None

    def price(self, symbol: str) -> dict:
        """Return {ok, symbol, price, change, kind, msg}. Research data only."""
        s = (symbol or "").strip().lower().lstrip("$")
        if not s:
            return {"ok": False, "msg": "Which symbol? e.g. 'price btc' or 'price aapl'."}
        if s in CRYPTO:
            cid = CRYPTO[s]
            raw = self._get(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}"
                            f"&vs_currencies=usd&include_24hr_change=true")
            if raw:
                try:
                    d = json.loads(raw).get(cid, {})
                    price = d.get("usd"); chg = d.get("usd_24h_change")
                    if price is not None:
                        return {"ok": True, "symbol": s.upper(), "kind": "crypto",
                                "price": price, "change": chg,
                                "msg": f"{s.upper()} (crypto): ${price:,.2f}"
                                       + (f"  ({chg:+.2f}% 24h)" if chg is not None else "")}
                except (ValueError, KeyError):
                    pass
            return {"ok": False, "msg": f"Couldn't fetch a live price for {s.upper()} right now."}
        # stock via Stooq
        sym = s if "." in s else f"{s}.us"
        raw = self._get(f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcvn&h&e=csv")
        if raw:
            try:
                row = list(csv.DictReader(io.StringIO(raw)))[0]
                close = row.get("Close", "")
                if close and close not in ("N/D", ""):
                    name = row.get("Name", s.upper())
                    return {"ok": True, "symbol": s.upper(), "kind": "stock",
                            "price": float(close), "change": None,
                            "msg": f"{s.upper()} ({name}): ${float(close):,.2f}  [close {row.get('Date','')}]"}
            except (ValueError, KeyError, IndexError):
                pass
        return {"ok": False, "msg": f"Couldn't fetch a price for {s.upper()} (check the symbol, or markets may be closed)."}

    # ---- watchlist ----
    def add_watch(self, symbol: str) -> str:
        s = (symbol or "").strip().upper().lstrip("$")
        if not s:
            return "Which symbol should I watch? e.g. 'add btc to watchlist'."
        wl = self._load(self.watch_path, [])
        if s in wl:
            return f"{s} is already on your watchlist."
        wl.append(s); self._save(self.watch_path, wl)
        return f"Added {s}. Watchlist now: {', '.join(wl)}."

    def remove_watch(self, symbol: str) -> str:
        s = (symbol or "").strip().upper().lstrip("$")
        wl = self._load(self.watch_path, [])
        if s in wl:
            wl.remove(s); self._save(self.watch_path, wl)
            return f"Removed {s}. Watchlist: {', '.join(wl) or '(empty)'}."
        return f"{s} isn't on your watchlist."

    def watchlist_summary(self, live: bool = True) -> str:
        wl = self._load(self.watch_path, [])
        if not wl:
            return "Watchlist is empty. Add symbols, e.g. 'add btc to watchlist'."
        if not live:
            return "Watchlist: " + ", ".join(wl)
        lines = []
        for s in wl[:12]:
            p = self.price(s)
            lines.append("  " + (p["msg"] if p["ok"] else f"{s}: price unavailable"))
        return "Watchlist (live):\n" + "\n".join(lines)

    # ---- journal ----
    def add_journal_entry(self, idea: str) -> dict:
        entries = self._load(self.journal_path, [])
        entries.append({"idea": idea, "ts": datetime.now().isoformat(timespec="seconds"),
                        "status": "research", "result": None})
        ok = self._save(self.journal_path, entries)
        return {"ok": ok, "msg": f"Entry #{len(entries)} saved to local journal." if ok else "Save failed."}

    # ---- risk / reward ----
    @staticmethod
    def risk_reward(entry: float, stop: float, target: float) -> dict:
        risk = abs(entry - stop); reward = abs(target - entry)
        rr = round(reward / risk, 2) if risk else None
        return {"risk": round(risk, 4), "reward": round(reward, 4), "r_r": rr}

    def risk_reward_text(self, args: str) -> str:
        nums = []
        for tok in (args or "").replace(",", " ").split():
            try:
                nums.append(float(tok.lstrip("$")))
            except ValueError:
                pass
        if len(nums) < 3:
            return ("Give me three numbers: entry, stop, target. "
                    "e.g. 'risk reward 100 95 115'.")
        entry, stop, target = nums[0], nums[1], nums[2]
        r = self.risk_reward(entry, stop, target)
        verdict = ("a solid setup" if (r["r_r"] or 0) >= 2 else
                   "a thin setup — most disciplined traders want at least 2 to 1")
        return (f"Entry {entry}, stop {stop}, target {target}:\n"
                f"  Risk per unit: {r['risk']}\n  Reward per unit: {r['reward']}\n"
                f"  Reward-to-risk: {r['r_r']} to 1 — {verdict}.\n"
                "Position-size so the risk equals at most ~1% of your account.")
