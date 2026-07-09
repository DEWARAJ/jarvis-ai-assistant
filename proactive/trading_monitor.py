"""JARVIS v6.0 — Trading monitor: P&L, daily halt, position alerts."""
from __future__ import annotations
from proactive.system_monitor import Alert, Priority

_alerted_positions: set[str] = set()
_watchlist: dict[str, float] = {}

def add_price_alert(symbol: str, target_price: float) -> None:
    _watchlist[symbol] = target_price

def run(alert_queue, shutdown_event, trader=None) -> None:
    import time
    last_halted = False
    while not shutdown_event.is_set():
        try:
            if trader is not None:
                halted = getattr(trader, "_halted", False)
                if halted and not last_halted:
                    alert_queue.put(Alert("TRADING HALTED — daily loss limit",
                                          Priority.CRITICAL, "trading_monitor"))
                last_halted = halted
                if not halted and getattr(trader, "_active", False):
                    try:
                        from modules.trading_module import AlpacaClient
                        c = AlpacaClient()
                        acct = c.get_account()
                        if "error" not in acct:
                            equity = float(acct.get("equity",0))
                            last_eq = float(acct.get("last_equity",equity))
                            pl_pct = (equity - last_eq) / last_eq if last_eq else 0
                            if pl_pct <= -0.05:
                                alert_queue.put(Alert(
                                    f"DAILY LOSS {pl_pct*100:.1f}% — AUTO-HALT",
                                    Priority.CRITICAL, "trading_monitor"))
                            elif pl_pct <= -0.03:
                                alert_queue.put(Alert(
                                    f"Daily loss {pl_pct*100:.1f}% — warning",
                                    Priority.MEDIUM, "trading_monitor"))
                        for pos in c.get_positions():
                            sym = pos["symbol"]
                            plpc = float(pos.get("unrealized_plpc",0))
                            key = f"{sym}_{int(plpc*100)}"
                            if plpc <= -0.08 and key not in _alerted_positions:
                                alert_queue.put(Alert(f"{sym} down {plpc*100:.1f}%",
                                    Priority.CRITICAL, "trading_monitor"))
                                _alerted_positions.add(key)
                            elif plpc <= -0.05 and key not in _alerted_positions:
                                alert_queue.put(Alert(f"{sym} down {plpc*100:.1f}%",
                                    Priority.HIGH, "trading_monitor"))
                                _alerted_positions.add(key)
                    except Exception: pass
        except Exception: pass
        shutdown_event.wait(timeout=60)
