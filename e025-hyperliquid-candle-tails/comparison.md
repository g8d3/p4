# e025 — A/B test: 3 agents vs 1 agent

Both paths consumed the same `ag-01-data/output/candles_raw.csv` (downloaded
once). Comparison written from the two `session-log.md` files + `diff` of the
outputs. Fill this in after both paths complete.

## Output parity

| File | Path A (sha256) | Path B (sha256) | Identical? |
|---|---|---|---|
| `stats.csv` | | | |
| `hist_5m.csv` | | | |
| `hist_1h.csv` | | | |
| `hist_1d.csv` | | | |
| `hist_1w.csv` | | | |
| `cond_next.csv` | | | |

Parity is expected to be close but not necessarily byte-identical (equal-width
bins depend on bin-edge rounding; conditional signals on same thresholds
should match). Any divergence must be explained in the notes below.

## Wall-clock time

| | Path A (ag-02 + ag-03) | Path B (ag-04) |
|---|---|---|
| Start | | |
| End | | |
| Total | | |

## Problems encountered

| Path | Problem | Solved how | Cost (time/tokens) |
|---|---|---|---|
| A | | | |
| B | | | |

## Verdict

- Which path finished faster?
- Which had fewer/smaller problems?
- Output quality (parity + report depth)?
- Context pressure (did either path feel long / need corrections)?
- **Winner and why.**

## Honest caveats

- N=1 experiment. The download was shared (the 3-agent split's real cost is
  duplicated orchestration, which is invisible here — both read the same CSV).
- Path A's ag-03 read only the CSV, so it re-derived columns ag-02 already
  computed — that duplication is part of the comparison.
