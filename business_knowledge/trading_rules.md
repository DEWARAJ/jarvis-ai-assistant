# Trading Rules & Discipline (JARVIS standing doctrine)

JARVIS NEVER places live trades. Research, analysis, backtests, paper trading, and
journaling only. Live order placement is Class B and always requires Master's explicit,
per-trade confirmation. Nothing here is financial advice; markets carry risk of loss.

## 1. Capital & Risk (non-negotiable)
- Risk per trade: <= 1% of account equity. Hard cap 2% only on A+ setups.
- Total open risk (sum of all live positions' risk) <= 5% of equity at any time.
- Define the invalidation/stop BEFORE entry. No stop = no trade.
- Position size = (account * risk%) / (entry - stop distance). Size to the stop, never to conviction.
- Minimum reward:risk = 2:1. Below that, pass — the edge isn't worth the variance.
- Max 3 new positions per day. After 2 consecutive losses, stop for the session (tilt guard).

## 2. Pre-Trade Checklist (every entry must pass all)
1. Thesis — one sentence: why this, why now.
2. Invalidation — exact price/condition that proves the thesis wrong.
3. Catalyst & timeframe — what moves it, over what horizon.
4. R:R — measured to a realistic target, not a hopeful one. >= 2:1.
5. Size — passes the 1% rule at the chosen stop.
6. Correlation — not just another expression of a position already held.
7. Liquidity — can exit the full size without moving the market against you.

## 3. Process Discipline
- No revenge trades, no FOMO entries, no averaging down a loser past the stop.
- Plan the trade, trade the plan. Move stops only in the direction of the trade (to lock gains), never away.
- Scale out into strength; let a runner ride with a trailing stop once at +1R.
- Journal EVERY trade: thesis, entry, stop, exit, R multiple, and the mistake (there's always one).

## 4. Strategy Validation Ladder (before any real capital)
1. Backtest on out-of-sample data (split train/test; beware overfitting & lookahead bias).
2. Walk-forward test (rolling windows) — confirms the edge isn't curve-fit to one regime.
3. Paper trade live for >= 20 trades — confirms execution, slippage, and psychology.
4. Only then, smallest real size. Scale up only after the live sample matches the backtest.
- Track: win rate, avg R, expectancy (= winrate*avgWin - lossrate*avgLoss), max drawdown, Sharpe.
- A positive-expectancy system with a survivable drawdown beats a high win-rate system that blows up.

## 5. Market Regime Awareness
- Identify regime first: trending vs range-bound vs high-volatility. Strategies are regime-specific.
- Trend-following dies in chop; mean-reversion dies in trends. Match tool to regime.
- Respect macro: Fed/rates, CPI, earnings, options-expiry (OPEX), and major data releases move everything.

## 6. Hard Don'ts
- No trading the open's first 5 minutes on emotion (let the auction settle).
- No naked options selling without defined risk.
- No position you can't explain to a skeptic in one sentence.
- No leverage that makes a normal adverse move a margin call.
