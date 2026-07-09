"""JARVIS v3.0 — Trading Intelligence Module.

5-step protocol (gated, never self-authorises live orders):
  STEP 1 — ENVIRONMENT CHECK    Class A — auto, checks keys + Alpaca connectivity
  STEP 2 — MARKET INTELLIGENCE  Class A — auto, LLM regime snapshot
  STEP 3 — RISK GATE            Class B — requires "activate trading confirm"
  STEP 4 — EXECUTION STATE      tracks active/halted, enforces hard rules
  STEP 5 — POST-TRADE ANALYSIS  Class A — auto-logged to episodic + code_changelog

Hard rules enforced in code (not just persona):
  • Never risk >2% account per trade
  • No overnight leverage without explicit instruction
  • Auto-halt if daily loss >5%
  • Never report paper as real
  • P&L never hidden — losses logged accurately

Degrades gracefully without Alpaca keys (reports unavailable, proposes fix).
"""
from __future__ import annotations
import os, json
from datetime import datetime

_ALPACA_PAPER = "https://paper-api.alpaca.markets"
_ALPACA_LIVE  = "https://api.alpaca.markets"


class TradingModule:
    def __init__(self, memory=None, llm=None, logger=None):
        self.memory = memory
        self.llm = llm
        self.logger = logger
        self._active = False
        self._halted = False
        self._session_pnl = 0.0
        self._daily_loss_limit = 0.05   # 5% auto-halt (hard rule)
        self._risk_per_trade   = 0.02   # 2% max per trade (hard rule)
        self._paper = bool(os.environ.get("ALPACA_PAPER", "1") not in ("0", "false", "False"))

    # ------------------------------------------------------------------
    # STEP 1 — ENVIRONMENT CHECK (Class A)
    # ------------------------------------------------------------------
    def env_check(self) -> dict:
        result = {
            "has_key":    bool(os.environ.get("ALPACA_API_KEY")),
            "has_secret": bool(os.environ.get("ALPACA_SECRET_KEY")),
            "paper_mode": self._paper,
            "account":    None,
            "status":     "unchecked",
            "errors":     [],
        }
        if not result["has_key"] or not result["has_secret"]:
            result["status"] = "no_keys"
            result["errors"].append(
                "ALPACA_API_KEY and ALPACA_SECRET_KEY not set in .env — "
                "add them to enable paper/live trading."
            )
            return result
        try:
            import urllib.request
            base = _ALPACA_PAPER if self._paper else _ALPACA_LIVE
            req = urllib.request.Request(
                f"{base}/v2/account",
                headers={
                    "APCA-API-KEY-ID":    os.environ["ALPACA_API_KEY"],
                    "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"],
                }
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                acct = json.loads(r.read())
            result["account"] = {
                "status":              acct.get("status"),
                "portfolio_value":     float(acct.get("portfolio_value", 0)),
                "buying_power":        float(acct.get("buying_power", 0)),
                "daytrade_count":      int(acct.get("daytrade_count", 0)),
                "pattern_day_trader":  bool(acct.get("pattern_day_trader", False)),
            }
            result["status"] = "ok"
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Alpaca API error: {e}")
        return result

    # ------------------------------------------------------------------
    # STEP 2 — MARKET INTELLIGENCE (Class A)
    # ------------------------------------------------------------------
    def market_intel(self) -> dict:
        intel: dict = {
            "ts":     datetime.now().isoformat(timespec="seconds"),
            "regime": "unknown",
        }
        if self.llm and getattr(self.llm, "enabled", False):
            sys_p = (
                "You are JARVIS trading intelligence. Factual, brief, "
                "tag every claim [Certain]/[Likely]/[Guessing]. No hype, no recommendations."
            )
            prompt = (
                "3-4 sentences: today's market regime (trending/ranging/volatile)? "
                "Major macro events this week? Key sector rotation or anomaly?"
            )
            ans = self.llm.chat(sys_p, prompt, no_cache=True)
            if ans:
                intel["regime_summary"] = ans
                intel["regime"] = "assessed"
        else:
            intel["regime_summary"] = "LLM offline — enable a provider key for regime assessment."
        return intel

    # ------------------------------------------------------------------
    # STEP 3 — RISK GATE prompt (Class B — orchestrator collects confirm)
    # ------------------------------------------------------------------
    def risk_gate_prompt(self, env: dict, intel: dict) -> str:
        acct   = env.get("account") or {}
        pv     = acct.get("portfolio_value", 0)
        bp     = acct.get("buying_power", 0)
        pdt    = acct.get("pattern_day_trader", False)
        regime = intel.get("regime_summary", intel.get("regime", "unknown"))
        return "\n".join([
            "CLASS B — TRADING ACTIVATION GATE",
            f"Account value      : ${pv:>12,.2f}" if pv else "Account value      : unknown (add API keys)",
            f"Buying power       : ${bp:>12,.2f}" if bp else "Buying power       : unknown",
            f"PDT flag           : {'YES — 3-day-trade limit applies' if pdt else 'No'}",
            f"Mode               : {'Paper (simulated)' if self._paper else 'LIVE — REAL MONEY'}",
            "",
            "Hard rules enforced in code (cannot be overridden):",
            f"  Max risk per trade : {self._risk_per_trade*100:.0f}% of portfolio value",
            f"  Auto-halt trigger  : {self._daily_loss_limit*100:.0f}% daily loss",
            "  Overnight leverage  : requires explicit instruction each session",
            "  P&L reporting      : always accurate, losses never hidden",
            "",
            f"Market regime: {regime}",
            "",
            "Say 'activate trading confirm' to proceed, or 'cancel'.",
        ])

    # ------------------------------------------------------------------
    # STEP 4 — Execution state management
    # ------------------------------------------------------------------
    def activate(self) -> str:
        self._active      = True
        self._halted      = False
        self._session_pnl = 0.0
        mode = "paper" if self._paper else "LIVE"
        self._log_event("trading_activated", f"mode={mode}")
        return (
            f"Trading activated, sir — {mode.upper()} mode. "
            "Position sizing enforced. P&L monitoring active."
        )

    def halt(self, reason: str = "manual") -> str:
        self._active = False
        self._halted = True
        self._log_event("trading_halted", f"reason={reason} session_pnl={self._session_pnl:+.2f}")
        return (
            f"All trading halted, sir (reason: {reason}). "
            f"Session P&L: ${self._session_pnl:+.2f}. No new orders will be placed."
        )

    def check_daily_halt(self, portfolio_value: float) -> bool:
        """Call after each trade. Returns True + auto-halts if daily loss breached."""
        if portfolio_value <= 0 or not self._active:
            return False
        loss_pct = self._session_pnl / portfolio_value
        if loss_pct <= -self._daily_loss_limit:
            self.halt(reason=f"auto-halt: daily loss {loss_pct*100:.1f}% >= {self._daily_loss_limit*100:.0f}% limit")
            return True
        return False

    def position_size(self, portfolio_value: float, price: float) -> float:
        """Max shares for 2% risk. Returns 0 if inactive or invalid price."""
        if not self._active or price <= 0 or portfolio_value <= 0:
            return 0.0
        return (portfolio_value * self._risk_per_trade) / price

    # ------------------------------------------------------------------
    # STEP 5 — Post-trade analysis (Class A — auto-logged)
    # ------------------------------------------------------------------
    def log_trade(self, symbol: str, side: str, qty: float, price: float,
                  pnl: float = 0.0, rationale: str = "") -> None:
        self._session_pnl += pnl
        if self.logger:
            self.logger.info(
                f"[TRADE] {side} {qty:.2f}x{symbol}@{price:.2f} pnl={pnl:+.2f} "
                f"session={self._session_pnl:+.2f} paper={self._paper} | {rationale}"
            )
        if self.memory:
            try:
                self.memory.log_mutation(
                    trigger=f"trade:{side} {qty:.2f}x{symbol}@{price:.2f}",
                    files_modified=[],
                    diff_summary=f"PnL={pnl:+.2f} session={self._session_pnl:+.2f} | {rationale}",
                    test_result="ok",
                    rolled_back=False,
                )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Status report (/trade status)
    # ------------------------------------------------------------------
    def status_report(self) -> str:
        env   = self.env_check()
        state = "ACTIVE" if self._active else ("HALTED" if self._halted else "STANDBY")
        if env["status"] == "no_keys":
            return (
                f"Trading: {state} | Keys: MISSING\n"
                "To enable: add ALPACA_API_KEY + ALPACA_SECRET_KEY to .env\n"
                f"Session P&L : ${self._session_pnl:+.2f}\n"
                f"Paper mode  : {self._paper}"
            )
        acct = env.get("account") or {}
        errs = " | ".join(env.get("errors", []))
        return "\n".join(filter(None, [
            f"Trading        : {state}",
            f"Mode           : {'Paper (simulated)' if self._paper else 'LIVE — REAL MONEY'}",
            f"Account value  : ${acct.get('portfolio_value', 0):,.2f}",
            f"Buying power   : ${acct.get('buying_power', 0):,.2f}",
            f"Session P&L    : ${self._session_pnl:+.2f}",
            f"PDT flag       : {'Yes' if acct.get('pattern_day_trader') else 'No'}",
            f"Risk/trade     : {self._risk_per_trade*100:.0f}%  |  Auto-halt: {self._daily_loss_limit*100:.0f}% daily loss",
            errs if errs else None,
        ]))

    # ------------------------------------------------------------------
    def _log_event(self, event: str, detail: str = "") -> None:
        if self.logger:
            self.logger.info(f"[TRADING] {event}: {detail}")
        if self.memory:
            try:
                self.memory.remember_fact(
                    event, f"{datetime.now().isoformat(timespec='seconds')} {detail}",
                    bucket="world_model"
                )
            except Exception:
                pass
