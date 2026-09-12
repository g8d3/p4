# e060 — DEPLOYED (rung 2, 2026-09-12)

Dexscreener-only rotation radar (owner decision: cheapest/free, $0).
No paid social pipe; rotation proxy = boost attention $ x on-chain
velocity (volume/txns). Social velocity + traders view deferred
(no free Dexscreener trader API — owner inbox noted).

## Rung-2 evidence

- Live URL (tailnet): `http://100.102.52.59:8323/` — curl 200 via tailnet,
  verified 2026-09-12 (~09:30 UTC leg). `/health` returns
  `{"ok": true, "track": "e060"}`. Binds `0.0.0.0:8323` (PID verified
  serving from this dir).
- Survives reboot: `@reboot cd .../e060-social-memecoin-radar &&
  python3 app.py >> server.log 2>&1` present in crontab.
- Freshness / stale-badge: `/api/rotation` LIVE at verify time
  (stale=false, age <1 min, 15 rows, source=dexscreener-free).
  5-min file cache in `data/rotation.json`; serves stale-badged cache
  with reason when Dexscreener unreachable; dashboard shows LIVE/STALE badge.
- Secrets: none in repo (free API, no keys; grep clean).

## What it proves

Free rotation radar is servable over the tailnet to the owner;
boost-ranked tokens with volume/price-change render in dashboard + JSON.
Next rung (TESTED): paper-track rotation calls for 2 weeks (kill rule:
no signal → kill) with monitored errors, not silent.

## Rung-3 evidence (TESTED, 2026-09-12 leg)

- e2e: `tests/e2e.sh` asserts dashboard 200 + title, `/health`
  {ok:true,track:e060}, `/api/rotation` shape (rows>0, stale/ts
  present, row keys symbol/chain/rotation_score). PASS 2026-09-12
  (15 rows, stale=false via tailnet :8323).
- Paper-tracked: `bin/paper_snapshot.py` appends daily top-10 call
  record to `paper/calls.jsonl` (date/ts/stale/score/boost/vol/chg);
  first snapshot 2026-09-12 logged. Daily cron `17 7 * * *`
  feeds the 2-week kill-rule evaluation.
- Monitored, not silent: `bin/healthcheck.sh` every 15 min
  (`*/15` cron) curls /health; silent on 200, on failure logs +
  `ops.py beat e060 blocked`. Verified healthy (exit 0).
- Spend: T0 free (local curls + free Dexscreener reads only).
