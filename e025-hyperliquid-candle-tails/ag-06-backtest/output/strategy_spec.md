# ag-06 — Part 2: Strategy spec (the exact rulebook we will backtest)

Date: 2026-08-13
Scope: research test on historical 1d candles, **not** a production system,
**not** trading advice.

## Plain English

A "strategy spec" is the recipe for a machine. Before you can test whether an
idea makes money, you must write down exactly what to buy, when to buy it,
when to sell it, and how much money is in play — with **no room for a human
to improvise**. If the recipe is vague, any result you get is meaningless,
because you don't know what you actually tested. This file is that recipe.

Three recipes are defined so we can compare:

- **Rule A** — the idea we want to test (the weekday tilt).
- **Rule B** — a "control". If Rule A is a real edge, Rule B should do worse.
  If both do the same, the edge is probably not real.
- **Rule C** — the boring baseline: just be long the market. Everything must
  beat this to be interesting.

## The one return we always use (read this twice)

The strategy enters at the **day open** and exits at the **day close**, so a
trade's P&L is the **intraday** return:

```
long P&L  = (close − open) / open × 100      (in %)
short P&L = (open − close) / open × 100
```

This is **not** the same as ag-05's `ret_next` (close-to-close return of the
*next* candle). The spec deliberately trades open→close of the *same* day.
The whole experiment is careful about this difference — see the backtest
report, because it turns out to matter enormously.

Weekdays refer to the **open day of the candle, UTC**. All prices are the
Hyperliquid 1d OHLC values from `candles_raw.csv`.

## Rule A — weekday tilt (the hypothesis)

| Weekday (candle open, UTC) | Action | Entry | Exit |
|---|---|---|---|
| Mon | **SHORT** | day open | day close |
| Tue | — | — | — |
| Wed | **SHORT** | day open | day close |
| Thu | **LONG** | day open | day close |
| Fri | — | — | — |
| Sat | — | — | — |
| Sun | **LONG** | day open | day close |

- No leverage (notional = equity per coin).
- Equal notional per coin: each coin gets the same slice of the portfolio.
- One position per coin per trading day.

## Rule B — control (the opposite tilt)

| Weekday (candle open, UTC) | Action |
|---|---|
| Mon | **SHORT** |
| Tue | **LONG** |
| Wed | **SHORT** |
| Thu | **SHORT** |
| Fri | **LONG** |
| Sat | **LONG** |
| Sun | **SHORT** |

Rule B trades **every** day, takes the *other* side of the pattern days
(short Thu/Sun where Rule A is long), and is long on the three days Rule A
ignores (Tue/Fri/Sat). If Rule A's edge is specific to Mon/Wed-down and
Thu/Sun-up, Rule B should underperform it. Same leverage and sizing as Rule A.

## Rule C — baseline

Two baselines, both reported:

- **C-daily**: LONG every day, open→close, every coin. Same trade structure
  as A and B, so expectancy/win-rate are directly comparable.
- **C-hold (buy-and-hold)**: buy each coin at its OOS start, hold to the OOS
  end, no daily trading. This is the "just don't do anything" benchmark.

## Pseudocode

```
for each coin C in [12 coins]:
    for each day D in C's out-of-sample window:
        w = weekday of D            # open day, UTC
        if Rule A:
            side = SHORT if w in {Mon, Wed} else LONG if w in {Thu, Sun} else NO_TRADE
        if Rule B:
            side = SHORT if w in {Mon, Wed, Thu, Sun} else LONG     # trades every day
        if Rule C:
            side = LONG                                             # trades every day
        if side is NO_TRADE: continue
        pnl = side == LONG ? (close - open)/open : (open - close)/open
        net = pnl - round_trip_fee                                  # fee per side, applied twice
        record (coin, day, rule, side, open, close, pnl, net)
```

## Fees (the same model used in the backtest)

Hyperliquid-style fee schedule, applied to notional, **per side**:

| Fee rate | Per side | Round trip (entry + exit) |
|---|---|---|
| **Taker** | 0.045% | **0.090%** |
| **Maker** | 0.018% | **0.036%** |

Every trade in the backtest is charged its round-trip fee (both sides), and
we report results **gross** (no fees), **net taker**, and **net maker**.
With per-day moves in the 0.2–0.6% range, a 0.09% round trip is a meaningful
friction — fees may decide whether the edge survives.

## Out-of-sample rule (how we stay honest)

The weekday pattern was discovered using **all** 1d data. To test it fairly
we only trade the **second half** of each coin's 1d series (split by time at
each coin's median timestamp) — the portion of history that was **never** used
to decide any rule. Part 3 states the exact date range used.
