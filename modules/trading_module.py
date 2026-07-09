"""JARVIS v6.0 — Alpaca trading with hard-coded risk limits."""
from __future__ import annotations
import os, json
from datetime import datetime
from pathlib import Path

try: import requests; _REQUESTS = True
except ImportError: _REQUESTS = False

_LOG_PATH = Path("memory") / "trade_log.jsonl"
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

MAX_RISK_PCT   = 0.02
DAILY_HALT_PCT = 0.05
MAX_ALLOC_PCT  = 0.25
MIN_BALANCE    = 100.0


class RiskViolation(Exception):
    pass


class AlpacaClient:
    def __init__(self):
        self.api_key    = os.getenv("ALPACA_API_KEY","")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY","")
        self.base_url   = os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets")
        self.paper_mode = "paper" in self.base_url
        self._headers   = {"APCA-API-KEY-ID": self.api_key,
                           "APCA-API-SECRET-KEY": self.secret_key}

    def _get(self, path: str) -> dict:
        if not _REQUESTS: return {"error": "requests not installed"}
        if not self.api_key: return {"error": "ALPACA_API_KEY not set"}
        try:
            r = requests.get(f"{self.base_url}/v2/{path}",
                             headers=self._headers, timeout=10)
            r.raise_for_status(); return r.json()
        except Exception as e: return {"error": str(e)}

    def _post(self, path: str, body: dict) -> dict:
        if not _REQUESTS: return {"error": "requests not installed"}
        try:
            r = requests.post(f"{self.base_url}/v2/{path}",
                              headers={**self._headers,"Content-Type":"application/json"},
                              json=body, timeout=10)
            r.raise_for_status(); return r.json()
        except Exception as e: return {"error": str(e)}

    def get_account(self) -> dict: return self._get("account")
    def get_positions(self) -> list[dict]:
        d = self._get("positions"); return d if isinstance(d, list) else []
    def get_latest_price(self, symbol: str) -> float | None:
        d = self._get(f"stocks/{symbol}/quotes/latest")
        try: return float(d["quote"]["ap"])
        except: return None

    def _pre_trade_check(self, symbol: str, qty: int, side: str) -> None:
        acct = self.get_account()
        if "error" in acct: raise RiskViolation(f"Cannot get account: {acct['error']}")
        equity = float(acct.get("equity",0))
        if equity < MIN_BALANCE:
            raise RiskViolation(f"Balance ${equity:.2f} below min ${MIN_BALANCE}")
        price = self.get_latest_price(symbol) or 0
        notional = qty * price
        if notional > equity * MAX_RISK_PCT:
            raise RiskViolation(f"Notional ${notional:.2f} > 2% limit ${equity*MAX_RISK_PCT:.2f}")
        pl = float(acct.get("equity",0)) - float(acct.get("last_equity",0))
        if pl < -(equity * DAILY_HALT_PCT):
            raise RiskViolation(f"Daily loss {pl:.2f} exceeds 5%. AUTO-HALT.")
        positions = {p["symbol"]: float(p["market_value"]) for p in self.get_positions()}
        if side == "buy" and (positions.get(symbol,0)+notional) > equity * MAX_ALLOC_PCT:
            raise RiskViolation(f"Would exceed 25% allocation for {symbol}")

    def place_order(self, symbol: str, qty: int, side: str,
                    order_type: str = "market", limit_price: float | None = None,
                    confirmed: bool = False) -> str:
        try: self._pre_trade_check(symbol, qty, side)
        except RiskViolation as e: return f"RISK GATE BLOCKED: {e}"
        body: dict = {"symbol": symbol, "qty": str(qty), "side": side,
                      "type": order_type, "time_in_force": "day"}
        if limit_price: body["limit_price"] = str(limit_price)
        result = self._post("orders", body)
        log_trade(symbol, side, qty, self.get_latest_price(symbol) or 0, 0.0, "JARVIS order")
        return f"Order: {result}"

    def cancel_all_orders(self, confirmed: bool = False) -> str:
        if not _REQUESTS: return "requests not installed."
        try:
            r = requests.delete(f"{self.base_url}/v2/orders",
                                headers=self._headers, timeout=10)
            return f"Cancelled. Status: {r.status_code}"
        except Exception as e: return f"Cancel error: {e}"

    def get_status_report(self) -> str:
        acct = self.get_account()
        if "error" in acct: return f"Alpaca error: {acct['error']}"
        positions = self.get_positions()
        mode = "PAPER" if self.paper_mode else "LIVE"
        equity = float(acct.get("equity",0))
        bp = float(acct.get("buying_power",0))
        pl = equity - float(acct.get("last_equity",equity))
        lines = [f"TRADING [{mode}]",
                 f"Equity: ${equity:,.2f} | BP: ${bp:,.2f}",
                 f"Today P&L: ${pl:+,.2f} ({pl/equity*100 if equity else 0:+.2f}%)",
                 f"Positions: {len(positions)}"]
        for p in positions[:5]:
            lines.append(f"  {p['symbol']}: {p['qty']}sh | "
                         f"P&L: ${float(p.get('unrealized_pl',0)):+.2f}")
        return "\n".join(lines)


class TradingSession:
    def __init__(self):
        self.client   = AlpacaClient()
        self._active  = False
        self._halted  = False

    def activate(self, confirmed: bool = False) -> str:
        self._active = True; self._halted = False
        return f"Trading ACTIVE. Mode: {'PAPER' if self.client.paper_mode else 'LIVE'}"

    def deactivate(self) -> str:
        self._active = False; return "Trading deactivated."

    def emergency_halt(self) -> str:
        self._active = False; self._halted = True
        result = self.client.cancel_all_orders(confirmed=True)
        log_trade("ALL","HALT",0,0,0,"Emergency halt")
        return f"EMERGENCY HALT — {result}"


def log_trade(symbol: str, side: str, qty: int, price: float,
              pnl: float, rationale: str) -> None:
    entry = {"ts": datetime.now().isoformat(timespec="seconds"),
             "symbol": symbol, "side": side, "qty": qty,
             "price": price, "pnl": pnl, "rationale": rationale}
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError: pass

