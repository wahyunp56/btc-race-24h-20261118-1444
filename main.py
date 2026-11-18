"""FlushDip: a one-asset dip-buying bot for the btc-race-24h replay.

Idea
----
A full-size round trip costs about 26 bps in fee, slippage and price impact,
so frequent small trades bleed out. This bot trades rarely, only into sharp
30-minute flushes, and exits on the bounce that usually follows one.

Rules (all integer math, no clock, no randomness, no network):
- Entry, flat only: the close has fallen at least 0.9% over the last 30 bars
  -> buy half the cash. A deeper flush (at least 1.8% over 30 bars) while
  still holding cash -> deploy the rest. No entries in the last 60 bars:
  a position opened that late would be flattened at the close for a loss.
- Exit, whole position: take profit at +1.5% over cost, stop loss at -1.5%.
  An exit the market refuses is re-sent on the next bar while its reason
  still holds.
- At most one order per reply; every order caps slippage at 100 bps past
  the close it was decided on, so a sell into a liquidity gap is refused
  (and re-sent) rather than filled for almost nothing.

Validation (local replica of the bars-replay/v1 fill model, fee 4 bps,
slippage 2 bps, constant-product impact against each bar's open depth):
- This competition's dev window (24h to the opening): +$13.51, 3 trades,
  max drawdown 1.5%. Dev gate: PASS.
- The previous race's dev window (24h to its opening): +$21.98, 5 trades,
  max drawdown 1.5%.
- Kit baselines on this dev window: buy-and-hold -$31.63, momentum -$23.87,
  ema-cross -$148.17, adx-momentum -$75.57, rsi-bollinger -$39.92,
  hold-cash $0.00. Every baseline fails the dev gate; this bot passes it.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
# A 30-bar drop of 0.9% opens a half position; 1.8% deploys the rest.
DROP1_NUM, DROP1_DEN = 991, 1000
DROP2_NUM, DROP2_DEN = 982, 1000
DROP_LOOKBACK = 30
# Half the cash on the first buy; the scale-in spends whatever cash is left.
FIRST_HALF_NUM, FIRST_HALF_DEN = 1, 2
# Take profit +1.5% over cost; stop loss -1.5%.
TAKE_NUM, TAKE_DEN = 1015, 1000
STOP_NUM, STOP_DEN = 985, 1000
MAX_SLIPPAGE_BPS = 100
# No entries once fewer than this many bars remain in the window.
NO_ENTRY_LAST = 60
WINDOW_BARS = 1440

closes = []


def on_batch(state, batch):
    bar = state.latest.get(SYMBOL)
    if bar is None:
        return []
    closes.append(int(bar["c"]))
    if state.warming_up:
        return []
    held = state.positions.get(SYMBOL)
    close = state.close(SYMBOL)
    if close is None:
        return []
    if held is not None and held.qty > 0:
        val = state.value(SYMBOL, held.qty)
        if val * TAKE_DEN >= held.cost * TAKE_NUM:
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        if val * STOP_DEN <= held.cost * STOP_NUM:
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        # Still holding cash and the flush deepened: deploy the rest.
        if state.cash * 4 > state.equity and len(closes) > DROP_LOOKBACK:
            ref = closes[-1 - DROP_LOOKBACK]
            if closes[-1] * DROP2_DEN <= ref * DROP2_NUM:
                return [{"side": "buy", "symbol": SYMBOL,
                         "notional_quote_units": state.cash,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    # Flat: only a sharp 30-bar flush opens a position. The sequence counts
    # warm-up batches too, so measure the no-entry tail from the first scored
    # batch, not from seq 0 (this competition sends no warm-up: the offset
    # is 0 here, and the guard is identical either way).
    if state.seq - state.warmup_bars >= WINDOW_BARS - NO_ENTRY_LAST:
        return []
    if len(closes) <= DROP_LOOKBACK:
        return []
    ref = closes[-1 - DROP_LOOKBACK]
    if closes[-1] * DROP1_DEN > ref * DROP1_NUM:
        return []
    amount = state.cash * FIRST_HALF_NUM // FIRST_HALF_DEN
    if amount < int(state.hello["fees"]["min_notional_quote_units"]):
        return []
    return [{"side": "buy", "symbol": SYMBOL, "notional_quote_units": amount,
             "max_slippage_bps": MAX_SLIPPAGE_BPS}]


makefun_bars.run(on_batch)
