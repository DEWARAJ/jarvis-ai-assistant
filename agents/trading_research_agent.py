from agents.base_agent import BaseAgent

RISK = ("\n[RISK] Research only. No trades are placed. No profit is guaranteed. "
        "Markets carry risk of loss. Paper-trade first; verify independently.")

class TradingResearchAgent(BaseAgent):
    role = "Trading research, journal, watchlist, risk plans. NEVER trades."
    risk = "high"
    def run(self, action, args="", plan=None):
        tool = self.tool("trading")
        if action == "trading_review":
            wl = tool.watchlist_summary() if tool else "(trading tool unavailable)"
            kb = self.knowledge("trading_rules", "markets_and_trading")
            thought = self.think(
                "Give a disciplined trading review: summarize the watchlist context, then walk a "
                "pre-trade risk checklist (thesis, invalidation, position size <= risk cap, R:R >= 2). "
                "Ground every point in the standing trading rules and markets knowledge provided. "
                "Tag claims [Certain]/[Likely]/[Uncertain]. "
                "Research only — never recommend placing a specific trade as a certainty.",
                context_note=(kb + "\n\nWatchlist:\n" + wl) if kb else wl)
            if thought:
                return self._header("Trading review", plan) + "\n" + thought + RISK
            return self._header("Trading review", plan) + (
                f"\n{wl}\n"
                "Pre-trade checklist: thesis, invalidation level, position size <= risk cap, "
                "R:R >= 2, no revenge trades." + RISK)
        if action == "journal_entry":
            if not args:
                return "Usage: create trading journal entry <idea + rationale>" + RISK
            res = tool.add_journal_entry(args) if tool else {"ok": False, "msg": "tool unavailable"}
            note = self.think(
                f"Briefly structure this trading idea into thesis + invalidation + risk plan: {args}",
                context_note="Research only; do not place trades.") or ""
            tail = ("\n" + note) if note else ""
            return (self._header("Trading journal entry saved (local)", plan) + "\n" + res.get("msg", "")
                    + tail + RISK) if res.get("ok") else (res.get("msg", "save failed") + RISK)
        return super().run(action, args, plan) + RISK
