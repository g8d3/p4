
# checkout-agent (example loop) — per-turn tax

**Measured** 2026-10-17, 187 turns (50 no-op turns + 137 live turns from our own fleet), harness `agent-loop --once, one process per turn`,
model `deepseek-v4.1-flash` via `DeepSeek`, machine `one Linux box, 8 cores, local SSD`.
**Process model:** one process per turn (so boot is paid every turn) — decides whether boot is in the
per-turn cost.



## 1. Where one turn goes

| segment | median | p90 | how it is measured |
|---|---|---|---|
| boot (process start → first event) | 372 ms [measured] | 377 ms [measured] | timestamp the first line of the run, outside the harness |
| pre-response (turn start → assistant message start) | 1554 ms [measured] | 1748 ms [measured] | arrival timestamps of the two events |
| stream (first token → end) | 3 ms [measured] | 7 ms [measured] | same |
| tools | 0 ms [measured] | 0 ms [measured] | tool end events |
| **total wall per turn** | 1.97 s [measured] | 2.3 s [measured] | process wall, measured from outside |

The rows do not sum exactly to the total: the total is process wall (1974 ms) while each row is that segment's median, leaving 45 ms [measured] of process exit, teardown and bookkeeping, which no single event delimits.

Note we do **not** split pre-response into dispatch vs provider: nothing exposed outside
the harness separates them. We report the bound.

## 2. What it costs at your volume

- turns/day: 1,000 (10 loops x 100 turns/day) [example] → 0.55 wall-hours/day, 137 wall-hours/year
- of which boot: 26 h/year (**removable**: keep the process warm)
- of which pre-response: 108 h/year (provider + dispatch; not removable from here)
- token line: $1,410/year at DeepSeek list ($0.27 in / $1.10 out per MTok) [example], 70% cached [assumption]
- wasted turns: 3.2% failed/aborted/empty [measured on our fleet] (16 of 500 turns in our own sample; we quote no dollar figure for them — every one of those errors ran on a model with no public list price, so the honest number is the rate, not a cost. Your exposure is the rate x your volume.)

## 3. The tail (this is what operators actually feel)

| | value |
|---|---|
| unaccounted p50 | 2.7 s [measured] |
| unaccounted p90 | 10.8 s [measured] |
| worst observed turn | 300 s [measured] |

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
- Limits: n per cell 5 reps for the decomposed one-word turn, jitter ±1 s run-to-run; cross-provider
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
