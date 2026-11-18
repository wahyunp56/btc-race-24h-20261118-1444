# FlushDip — strategy notes

## Idea

A full-size round trip costs about 26 bps in fee, slippage and price impact,
so frequent small trades bleed out. FlushDip trades rarely, only into sharp
30-minute flushes, and exits on the bounce that usually follows one. One open
position, full size, long only.

## Rules

- **Entry (flat only):** the close has fallen at least 0.9% over the last
  30 bars -> buy half the cash. While still holding cash, a deeper flush
  (at least 1.8% over 30 bars) -> deploy the rest. No entries in the last
  60 bars of the window: a position opened that late would be flattened at
  the close for a loss.
- **Exit (whole position):** take profit at +1.5% over cost, stop loss at
  -1.5%. An exit the market refuses is re-sent on the next bar while its
  reason still holds.
- **Orders:** at most 1 order per reply, max slippage 100 bps vs the
  decision close. All comparisons in integer math; no clock, no randomness,
  no network, no files outside the repository.

## Why this shape

On the 24 hours before this competition opened, Bitcoin drifted down 2.8%
with a 3.4% range. Conditional on a 30-minute drop of at least 1.0%, the
price bounced at least 1.0% within the next hour half the time (mean max
gain +1.07%); after a 1.2% drop, 58% of the time (mean max +1.16%). The
bounce is the edge; the 0.9%/1.8% two-tier entry buys the flush and then
the deeper flush, and the +1.5% take-profit banks the typical bounce. A
single-tier RSI dip-buyer (the previous race's entry) scored -$18.13 on
this window and fails the dev gate; every kit baseline loses on it too.

## Validation

Local replica of the bars-replay/v1 fill model (fee 4 bps, slippage 2 bps,
constant-product impact against each bar's open depth), run over the wire
protocol against the actual `main.py`:

- This competition's dev window: **+$13.51** (3 trades, max drawdown 1.5%).
  Dev gate: PASS.
- The previous race's dev window: **+$21.98** (5 trades, max drawdown 0.7%).
- Kit baselines on this dev window: buy-and-hold -$31.63, momentum -$23.87,
  ema-cross -$148.17, adx-momentum -$75.57, rsi-bollinger -$39.92,
  hold-cash $0.00. Every baseline fails the dev gate.

Parameter plateau (dev window / previous window): 30-minute drops of
0.8–0.9% to open and 1.5–1.8% to scale in, take-profit 1.5%, all score
+$13.3–13.5 / +$21.1–22.0. The stop-loss never fired on either window; it
is a safety net, not a tuned parameter. Time-based exits were tested and
rejected: they turn the dev window negative.

## Honest limits

- Two round trips a day at most, often one: the race-day result rides on
  whether 1–2 flushes arrive and bounce. The dev gate is passed with
  margin (+$13.51), but the race window is unseen and a quiet day scores
  near zero.
- The edge is mean reversion after a flush. On a day that trends down
  without bouncing, the stop-loss caps each round trip near -1.5% plus
  costs; on a day that trends up without flushing, the bot may not trade
  at all and scores $0 (failing the race guardrail of at least 1 trade,
  though the dev gate is what admits it to the race).
