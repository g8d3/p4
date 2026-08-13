# e025 — A/B test: 3 agents vs 1 agent

Both paths consumed the same `ag-01-data/output/candles_raw.csv` (135,232
rows, downloaded once in 82s). Both paths ran DeepSeek V4 Flash on opencode-go
(same model, kills the model confound). Filled in from the three
`session-log.md` files + checksum diff. N=1.

## Output parity

| File | Path A (ag-02) | Path B (ag-04) | Identical? |
|---|---|---|---|
| `stats.csv` | 48 rows, v=0 dropped | 48 rows, v=0 kept | **NO** |
| `hist_5m.csv` | n=60,277 | n=60,277 | **NO** (bin edge rounding) |
| `hist_1h.csv` | n=60,014 | n=60,014 | **NO** (bin edge rounding) |
| `hist_1d.csv` | n=10,250 | n=13,012 | **NO** (v=0) |
| `hist_1w.csv` | n=1,468 | n=1,881 | **NO** (v=0) |
| `cond_next.csv` | 988 rows (per-coin + pooled ALL) | 1,166 rows (extra ALL layer) | **NO** |

**Divergence root cause**: the 3,175 synthetic pre-listing candles (v=0) in
1d/1w. Path A dropped them from the base stats (documented + reasoned in
ag-02 session-log #1); Path B kept them in the base stats and ran the
exclusion as a separate robustness pass. Both documented the decision
honestly; the choice propagated to every artifact.

**Verdict agreement**: despite the artifact diff, both paths reached the SAME
scientific conclusions (fat tails everywhere; no directional edge; volatility
clustering is the real effect). The conclusion is robust to the divergence.

## Wall-clock time

| | Path A (ag-02 + ag-03, parallel) | Path B (ag-04) |
|---|---|---|
| Start | ~16:31 | 16:31:24 |
| End | 16:35:10 | 16:36:30 |
| Total | **~6 min** | **~5 min** |

Essentially tied. The shared download (82s) and the shared-input design mean
the split's orchestration cost is the only real difference.

## Problems encountered

| Path | Problem | Solved how | Cost |
|---|---|---|---|
| A (ag-02) | synthetic v=0 pre-listing rows in 1d/1w | dropped 3,175 before stats; documented | 1 probe + reasoning |
| A (ag-02) | naive bins centered off-0 for 1w | symmetric ±range bins, verified | small |
| A (ag-02) | cross-tf scale mismatch | z-score per (coin,tf) for overlay only | small |
| A (ag-02) | pandas kurtosis convention ambiguity | converted to raw (normal=3), stated convention | small |
| A (ag-03) | per-coin tail samples n<300 | added pooled coin=ALL z-layer; verdicts on pooled | structural decision |
| A (ag-03) | pivot KeyError on base rows | join against signal='base'; **3 wasted commands** | ~3 commands |
| A (ag-03) | numpy NaN warnings on n=1 groups | documented, kept NaN | none |
| B (ag-04) | pandas 2.x removed kurt(fisher=) | scipy.stats.kurtosis | small |
| B (ag-04) | boolean-mask reindex bug in groupby | per-group boolean columns | 1 retry |
| B (ag-04) | v=0 synthetic rows | kept in base + robustness pass (1d kurt 12.8→10.7) | 1 extra pass |
| B (ag-04) | model cannot view PNGs | verified via `file`/bytes | none |

Total: Path A **8 problems** (one costing 3 wasted commands), Path B **5
problems**. Comparable — the user's hypothesis ("3 agents will have more
problems") held only slightly, and the extra problems were mostly
orchestration-side, not agent-side.

## Command count & context

| | ag-02 | ag-03 | ag-04 |
|---|---|---|---|
| Shell commands | ~9 | 16 | 11 |
| Context reads | e000 (880 lines) + AGENTS.md + manifest.json (517 lines) | e000 + 3 AGENTS.md | e000 + 3 AGENTS.md |
| Self-wakes / corrections | 0 | 0 | 0 |

Path A total = 25 commands across 2 sessions; Path B = 11 in one. Path A also
reads e000 fundamentals **three times** (once per session) vs once.

## Verdict

- **Speed**: tied (~5-6 min). The compute is trivial; neither architecture's
  runtime matters here.
- **Problems**: Path B had fewer problems (5 vs 8) and no wasted commands.
  Path A's problems were no harder, just more of them.
- **Output quality**: Path A produced the cleaner artifact — ag-02's explicit
  v=0 drop is the "right" methodology for tail statistics, and its
  session-log passes that reasoning forward. Path B's kept-both choice is
  defensible but slightly muddier. Both reports reach identical conclusions.
- **Context pressure**: neither felt heavy; Path A spent 3× on context reads.
- **Winner**: **Path B (1 agent)** for this task, narrowly. Fewer commands,
  less orchestration, equal conclusions. The 3-agent split paid its overhead
  (3 launches, 3× context reads, provider failure on ag-03 → full restart of
  all three windows) for no measurable quality gain on a ~5-minute job.

## Honest caveats

- **N=1, and the orchestration incident confounds it**: ag-03's first launch
  (cmd provider) died at startup; all three windows were restarted on the same
  model. That restart is a real 3-agent cost (more moving parts = more failure
  surface), but it inflates the comparison against Path A.
- The download was shared — in a real project, the 3-agent split's win is
  incremental/parallelizable work and resumable checkpoints (ag-02 can re-run
  without re-fetching). This task is too small for that to matter.
- Same model everywhere was deliberate; with different models the problems and
  quality would diverge differently.

## Recommendation

1 agent for jobs under ~30 min of agent-time; split into 3 only when stages
are independently re-runnable, need different tools, or run on different
providers for throughput (e.g. this experiment's ag-01 data layer, which IS a
justifiable separate agent — it's the only stage that can fail independently
and has resumable value).
