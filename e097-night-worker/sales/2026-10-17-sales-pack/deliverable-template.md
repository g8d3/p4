# The deliverable: `breakdown.md` (one page per loop)

This is the exact shape of what a client receives. Every field is something we know how
to measure after this run, and nothing here depends on a lever we retracted (cache
discipline, startup-scan scoping, a size slope — see the paper's sections 6-8).

Placeholders are written as `«...»`. No client numbers are invented in this file.

---

# «loop name» — per-turn tax

**Measured** «date», «n» turns («no-op series» + «live turns»), harness `«command»`,
model `«model»` via `«provider»`, machine `«machine»`.
**Process model:** «one process per turn / warm process» — decides whether boot is in the
per-turn cost.

«notes»

## 1. Where one turn goes

| segment | median | p90 | how it is measured |
|---|---|---|---|
| boot (process start → first event) | «boot-ms» | «boot-p90» | timestamp the first line of the run, outside the harness |
| pre-response (turn start → assistant message start) | «pre-ms» | «pre-p90» | arrival timestamps of the two events |
| stream (first token → end) | «stream-ms» | «stream-p90» | same |
| tools | «tools-ms» | «tools-p90» | tool end events |
| **total wall per turn** | «total-s» | «total-p90» | process wall, measured from outside |

«segment-note»

Note we do **not** split pre-response into dispatch vs provider: nothing exposed outside
the harness separates them. We report the bound.

## 2. What it costs at your volume

- turns/day: «turns-day» → «h-day» wall-hours/day, «h-year» wall-hours/year
- of which boot: «h-boot-year» h/year (**removable**: keep the process warm)
- of which pre-response: «h-pre-year» h/year (provider + dispatch; not removable from here)
- token line: «token-usd»/year at «price» «price-source», «cache-hit»% cached «cache-hit-source»
- wasted turns: «wasted-rate»% failed/aborted/empty [«wasted-source»] («waste-note»)

## 3. The tail (this is what operators actually feel)

| | value |
|---|---|
| unaccounted p50 | «unacc-p50» |
| unaccounted p90 | «unacc-p90» |
| worst observed turn | «worst» |

«outlier-n» runs in one cell were «k»x slower than that cell's median, in a contiguous
streak that then recovered. «outlier-cause»

## 4. What we would change, ranked by measured effect

| # | change | measured effect | confidence |
|---|---|---|---|
| 1 | «boot-cut» | «boot-cut-effect» | measured |
| 2 | «context-cut» | «context-cut-effect» | measured on your loop |
| 3 | «third-cut» | «third-cut-effect» | «third-cut-confidence» |

Explicitly **not** recommended, with reasons: cache discipline (did not reproduce, paper
§6); startup-scan scoping (startup does not scale with the session store, §7); a size
coefficient (mis-stated and not reproducible, §8).

## 5. The regression gate

Script `«gate-path»`, run `«gate-how»`. It fails when steady-state wall per turn exceeds
«baseline-x» or the wasted-turn rate exceeds «wasted-budget»%. This is the part that keeps
the cut from creeping back, and it stays after we leave.

## 6. Method and limits

- Protocol: 50 no-op turns (`Reply with exactly the word PONG. Call no tools.`) + live
  turns, same command, same machine, same day.
- Limits: n per cell «n-per-cell», jitter ±«jitter-s» s run-to-run; cross-provider
  comparisons are confounded; single samples are anecdotes, not rates.
- Raw logs: «logs-path». You keep them.

---

## What this page guarantees

1. Every figure is labelled *measured* (ours, same numbers as the paper), *example* (the
   illustrative shape above) or *assumption* (a parameter you replace). No exceptions.
2. Negative results are stated (section 4's "not recommended" block): if you later find
   that we sold you a retracted lever, that is a reference we never get back.
3. The regression gate is delivered, not just described: the value of the audit after we
   leave is the gate, not the report.
