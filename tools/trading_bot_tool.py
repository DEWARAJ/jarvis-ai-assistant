"""Smart-Trader bot control for JARVIS.

Wraps the external smart-trader CLI (C:\\Users\\dewar\\Desktop\\smart-trader):
    python smart_trader.py signals            one live scan, prints recommendations
    python smart_trader.py backtest [DAYS]    walk-forward historical sim
    python smart_trader.py walkforward [DAYS] out-of-sample validation
    python smart_trader.py paper              continuous paper trading on Alpaca

Class model (enforced by the orchestrator, mirrored here for honesty):
  CLASS A (auto): signals, backtest, walkforward, pnl/positions/log reads.
  CLASS B (confirm once): paper_start — opens an unattended broker-account
          connection and places paper orders continuously. paper_stop is safe.

This tool NEVER places a real-money order: the bot only supports Alpaca PAPER.
It never fakes output — it returns the bot's real stdout/stderr.
"""
from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path

from tools.base_tool import BaseTool

DEFAULT_BOT_DIR = r"C:\Users\dewar\Desktop\smart-trader"


class TradingBotTool(BaseTool):
    name = "trading_bot"
    scope = "control the smart-trader bot (signals / backtest / paper)"

    def __init__(self, context=None, logger=None):
        super().__init__(context, logger)
        cfg = (self.context.get("settings") or {}) if isinstance(self.context, dict) else {}
        self.bot_dir = Path(cfg.get("trading_bot_dir") or DEFAULT_BOT_DIR)
        self.entry = self.bot_dir / "smart_trader.py"
        self._paper_proc = None  # background paper-trading process

    # ---- internals -----------------------------------------------------
    def _ready(self) -> tuple[bool, str]:
        if not self.entry.exists():
            return (False, f"smart_trader.py not found at {self.entry}")
        return (True, "")

    def _run(self, args: list[str], timeout: int) -> dict:
        ok, why = self._ready()
        if not ok:
            return {"ok": False, "spoken": f"I can't reach the trading bot, sir - {why}.", "debug": why}
        try:
            r = subprocess.run(
                [sys.executable, str(self.entry), *args],
                cwd=str(self.bot_dir), capture_output=True, text=True, timeout=timeout,
            )
            out = ((r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")).strip()
            return {"ok": r.returncode == 0, "raw": out, "rc": r.returncode,
                    "debug": f"rc={r.returncode}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "raw": "", "spoken": "The bot took too long and I stopped it, sir.",
                    "debug": "timeout"}
        except Exception as e:
            return {"ok": False, "raw": "", "spoken": f"I couldn't run the bot, sir ({e}).", "debug": str(e)}

    @staticmethod
    def _tail(text: str, n: int = 1800) -> str:
        text = text or ""
        return text if len(text) <= n else "...\n" + text[-n:]

    # ---- CLASS A: read-only / simulation -------------------------------
    def signals(self) -> dict:
        """One live scan of the universe; prints TAKE/skip recommendations. No orders."""
        r = self._run(["signals"], timeout=180)
        if "spoken" in r:
            return r
        body = self._tail(r["raw"]) or "No output from the scan, sir."
        return {"started": r["ok"], "spoken": f"Here is the latest scan, sir.\n{body}", "debug": r["debug"]}

    def backtest(self, days: int = 30) -> dict:
        """Walk-forward historical simulation. Pure analysis, no orders."""
        try:
            days = max(1, int(days))
        except Exception:
            days = 30
        r = self._run(["backtest", str(days)], timeout=600)
        if "spoken" in r:
            return r
        body = self._tail(r["raw"]) or "The backtest produced no report, sir."
        return {"started": r["ok"], "spoken": f"Backtest over {days} days, sir.\n{body}", "debug": r["debug"]}

    def walkforward(self, days: int = 45) -> dict:
        """Out-of-sample validation: does the brain's gating add real edge?"""
        try:
            days = max(1, int(days))
        except Exception:
            days = 45
        r = self._run(["walkforward", str(days)], timeout=600)
        if "spoken" in r:
            return r
        body = self._tail(r["raw"]) or "Walk-forward produced no report, sir."
        return {"started": r["ok"], "spoken": f"Walk-forward validation over {days} days, sir.\n{body}", "debug": r["debug"]}

    def pnl(self) -> dict:
        """Summarise the closed-trade log (data/trade_log.csv): trades, win rate, avg R."""
        path = self.bot_dir / "data" / "trade_log.csv"
        if not path.exists():
            return {"started": False, "spoken": "No trade log yet, sir - run a backtest or paper session first.",
                    "debug": str(path)}
        try:
            import csv
            rows = list(csv.DictReader(open(path, encoding="utf-8")))
        except Exception as e:
            return {"started": False, "spoken": f"I couldn't read the trade log, sir ({e}).", "debug": str(e)}
        if not rows:
            return {"started": True, "spoken": "The trade log is empty, sir.", "debug": "0 rows"}
        n = len(rows)
        wins = sum(1 for r in rows if str(r.get("outcome", "")).strip() in ("1", "1.0"))
        def _f(v):
            try: return float(v)
            except Exception: return 0.0
        avg_r = sum(_f(r.get("r_multiple")) for r in rows) / n
        wr = wins / n if n else 0.0
        return {"started": True,
                "spoken": (f"Trade log, sir: {n} trades, win rate {wr:.0%} ({wins} wins, {n-wins} losses), "
                           f"average R {avg_r:+.3f}."),
                "debug": f"n={n} wr={wr:.3f} avgR={avg_r:.3f}"}

    # ---- CLASS B: continuous broker connection -------------------------
    def paper_dry_run(self) -> dict:
        """Report exactly what paper_start WOULD do, before any confirmation."""
        key = bool(os.getenv("ALPACA_API_KEY")) and bool(os.getenv("ALPACA_SECRET_KEY"))
        lines = [
            "Dry run, sir - paper trading would:",
            f"  - launch: {sys.executable} {self.entry} paper",
            f"  - working dir: {self.bot_dir}",
            "  - connect to your Alpaca PAPER account (no real money)",
            "  - scan the universe each minute and place PAPER market orders on TAKE signals",
            "  - run continuously until you say 'stop paper trading'",
            f"  - Alpaca keys present: {'yes' if key else 'NO - it will refuse to start without them'}",
        ]
        return {"started": True, "spoken": "\n".join(lines), "debug": f"keys={key}"}

    def paper_start(self) -> dict:
        """Start continuous paper trading in the background. CLASS B - gate before calling."""
        ok, why = self._ready()
        if not ok:
            return {"started": False, "spoken": f"I can't reach the trading bot, sir - {why}.", "debug": why}
        if self._paper_proc and self._paper_proc.poll() is None:
            return {"started": True, "spoken": "Paper trading is already running, sir.", "debug": "already running"}
        if not (os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY")):
            return {"started": False,
                    "spoken": "I can't start paper trading, sir - ALPACA_API_KEY and ALPACA_SECRET_KEY are not set.",
                    "debug": "missing alpaca keys"}
        try:
            log = open(self.bot_dir / "paper_session.log", "a", encoding="utf-8")
            self._paper_proc = subprocess.Popen(
                [sys.executable, str(self.entry), "paper"],
                cwd=str(self.bot_dir), stdout=log, stderr=subprocess.STDOUT,
            )
            return {"started": True,
                    "spoken": ("Paper trading is live, sir - Alpaca paper account, no real money. "
                               "I'm logging to paper_session.log. Say 'stop paper trading' to halt."),
                    "debug": f"pid={self._paper_proc.pid}"}
        except Exception as e:
            return {"started": False, "spoken": f"I couldn't start paper trading, sir ({e}).", "debug": str(e)}

    def paper_stop(self) -> dict:
        """Stop the background paper-trading process. Safe (Class A)."""
        if not self._paper_proc or self._paper_proc.poll() is not None:
            return {"started": False, "spoken": "Paper trading isn't running, sir.", "debug": "not running"}
        try:
            self._paper_proc.terminate()
            try:
                self._paper_proc.wait(timeout=10)
            except Exception:
                self._paper_proc.kill()
            self._paper_proc = None
            return {"started": True, "spoken": "Paper trading stopped, sir.", "debug": "terminated"}
        except Exception as e:
            return {"started": False, "spoken": f"I couldn't stop it cleanly, sir ({e}).", "debug": str(e)}

    def paper_status(self) -> dict:
        running = bool(self._paper_proc and self._paper_proc.poll() is None)
        return {"started": True,
                "spoken": "Paper trading is running, sir." if running else "Paper trading is not running, sir.",
                "debug": f"running={running}"}
