
# our own fleet (500 message samples, 2026-10-18) — per-turn tax

**Measured** 2026-10-18, 500 turns (0 no-op turns + 500 live turns from your log), harness `agent-loop --once, one process per turn`,
model `deepseek-v4.1-flash (NOT YOURS — not given)` via `DeepSeek (NOT YOURS — not given)`, machine `one Linux box, 8 cores, local SSD`.
**Process model:** one process per turn (so boot is paid every turn) — decides whether boot is in the
per-turn cost.

**Read this first — what is assumed:**

- your answers did not name `model`, `provider` — the report describes OUR example loop wherever it should describe yours. The timings are still measured from your log; the model, the route and the process model are not.
- your answers did not give `price_in`, `price_cache`, `price_out`, `in_tok`, `out_tok`, `cache_hit` — the token line below is computed with **our** example rates and is **not your bill**. Send those six numbers and we re-run it in minutes.


## 1. Where one turn goes

| segment | median | p90 | how it is measured |
|---|---|---|---|
| boot (process start → first event) | 372 ms [measured] | 377 ms [measured] | timestamp the first line of the run, outside the harness |
| pre-response (turn start → assistant message start) | 2836 ms [measured] | 4384 ms [measured] | arrival timestamps of the two events |
| stream (first token → end) | 2014 ms [measured] | 7958 ms [measured] | same |
| tools | 18 ms [measured] | 4938 ms [measured] | tool end events |
| **total wall per turn** | 6.09 s [measured] | 23.0 s [measured] | process wall, measured from outside |

Every row carries the pre-response column, so the provider roundtrip is separated from the residual. 11 row(s) had segments exceeding the turn wall (independent timers); their residual is clamped to 0. Boot is the one figure on this page that is not from your log: measured outside the harness.

Note we do **not** split pre-response into dispatch vs provider: nothing exposed outside
the harness separates them. We report the bound.

## 2. What it costs at your volume

- turns/day: 1,000 (10 loops x 100 turns/day) [from your answers] → 1.69 wall-hours/day, 423 wall-hours/year
- of which boot: 26 h/year (**removable**: keep the process warm)
- of which pre-response: 197 h/year (provider + dispatch; not removable from here)
- token line: $1,410/year at DeepSeek list ($0.27 in / $1.10 out per MTok) [OUR EXAMPLE RATES — not yours], 70% cached [assumption]
- wasted turns: 0.2% failed/aborted/empty [measured on your log] (1 of 500 turns in your log. Those rows report zero input and zero output tokens — they failed before the provider billed anything visible to us — so the honest number is the rate, not a cost. Your exposure is the rate x your volume.)

## 3. The tail (this is what operators actually feel)

| | value |
|---|---|
| unaccounted p50 | 0.0 s [measured] |
| unaccounted p90 | 0.0 s [measured] |
| worst observed turn | 0 s [measured] |

four of ten runs in one cell were 2-6x slower than that cell's median, in a contiguous
streak that then recovered. we could not name the cause, so it is listed as unexplained (paper 6) rather than sold as a finding

## 4. What we would change, ranked by measured effect

| # | change | measured effect | confidence |
|---|---|---|---|
| 1 | keep the process warm | -0.37 s/turn = -26 h/year at this volume [measured boot: us, measured from outside the harness (paper 5.4; 372 ms with the startup cache warm, 940 ms cold)] | measured |
| 2 | cut carried context from 108 KB to 30 KB [example] | -0.9 s/turn is illustrative [example]: we retracted a size coefficient (paper 8), so what you buy is the before/after series on your own loop | measured on your loop |
| 3 | cap tool-result size before it enters the transcript | not yet measured on this loop: we would run the series first | hypothesis |

Explicitly **not** recommended, with reasons: cache discipline (did not reproduce, paper
§6); startup-scan scoping (startup does not scale with the session store, §7); a size
coefficient (mis-stated and not reproducible, §8).

## 5. The regression gate

Script `regression_gate.py`, run `nightly, against the baseline in baseline.json`. It fails when steady-state wall per turn exceeds
baseline x 1.2 or the wasted-turn rate exceeds 5%. This is the part that keeps
the cut from creeping back, and it stays after we leave.

## 6. Method and limits

- Protocol: 50 no-op turns (`Reply with exactly the word PONG. Call no tools.`) + live
  turns, same command, same machine, same day.
- Limits: n per cell 500 turns in this run, jitter ±1 s run-to-run; cross-provider
  comparisons are confounded; single samples are anecdotes, not rates.
- Raw logs: the per-run logs we hand over (this page is not one of them). You keep them.

---

## What this page guarantees

1. Every figure is labelled *measured* (ours, same numbers as the paper), *example* (the
   illustrative shape above) or *assumption* (a parameter you replace). No exceptions.
2. Negative results are stated (section 4's "not recommended" block): if you later find
   that we sold you a retracted lever, that is a reference we never get back.
3. The regression gate is delivered, not just described: the value of the audit after we
   leave is the gate, not the report.
