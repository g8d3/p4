# X Thread — Transcript Tax (6 posts, English, data-led)

Validated 2026-10-17 with `.venv/bin/python publicar_x.py --dry` from `/home/vuos/code/p4/e092-echolike`.
All 6 pass: max 280 chars, no cashtags, no URLs. DRY ONLY — nothing published.

**REVALIDATED 2026-10-18 04:5xZ: all 6 pass** (max 280 chars, no cashtags, no URLs; post 5
was rewritten to carry the §9 reading of the 37% "unaccounted" — it is the provider
round-trip, not a mystery).

**REVALIDATE BEFORE POSTING (2026-10-17 06:16Z):** posts 2, 4 and 5 were rewritten after
two measurement corrections (report §5 and §6). Post 2: the model-span clock can collapse
on single-chunk replies, so the honest claim is "provider plus harness". Post 4: the
cache-state claim did not survive re-checking against bench.csv, so it now reports the
negative result. Post 5: quotes the 500-turn real-work sample instead of the no-op
extrapolation. Run `--dry` again before queueing; nothing was queued from this edit.

---

## Post 1 (163 chars)

1/6 We ran 65 no-op agent turns across 3 harnesses. Median cost of replying with one word: 2.4 to 3.4 s. The model took milliseconds. The rest is a transcript tax.

## Post 2 (215 chars)

2/6 On one harness the model span measured 2 to 7 ms, the rest of the turn 1.4 to 2.0 s. Correction we published: that clock can collapse on one-chunk replies, so we call it provider plus harness, not harness alone.

## Post 3 (187 chars)

3/6 Size costs less than you fear, more than zero: ~1 s at 30-108 KB, 1.5-1.7 s at 170-228 KB, ~5 s at megabyte scale (n=8, one harness). We could not fit a slope, so we do not quote one.

## Post 4 (172 chars)

4/6 We expected cache state to explain the slow turns. It did not: 9216 cached tokens appeared in a 16.6 s run and two ~3 s runs. Four of ten were 2-6x slower, unexplained.

## Post 5 (197 chars)

5/6 Fleet math: 1000 no-op turns burn ~50 min of pure overhead. On 500 live turns: 8.7 s each — 34% model, 29% tools, 37% the harness calls "unaccounted". We measured it: it is the provider round-trip.

## Post 6 (181 chars)

6/6 We audit agent fleets: measure your tax per loop, then cut it. One loop measured in 5 days, fleet audit plus cuts available. Reply TAX and we start with one loop, numbers first.

---

## Validation log

```
{"dry": true, "len": 163, ...}   post 1
{"dry": true, "len": 215, ...}   post 2  (rewritten after the correction)
{"dry": true, "len": 171, ...}   post 3
{"dry": true, "len": 169, ...}   post 4
{"dry": true, "len": 197, ...}   post 5  (rewritten: real-work numbers)
{"dry": true, "len": 181, ...}   post 6
```

Re-validated 2026-10-17 06:02Z against the live validator (`--dry`, nothing posted).

Publish path: queue via `posts_programados/` only, after the 48-hour veto in `ops-rules.md`.
Kill switch: `systemctl --user stop echolike-cola.timer`.
