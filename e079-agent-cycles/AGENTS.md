# e079 — Agent Cycles (continuous delivery board for itself)

Web app that manages agent cycles. Each cycle ships one new version.
The app is delivered BY cycles — dogfooding from v1.

## Product

| Surface | User action |
|---|---|
| Board `/` | See version, margin strip vs niche avg, start/finish next cycle, browse history. Presentable landing, no login. |
| Admin `/admin.html` | Token-gated: site config, MoR provider + API key paste (stored 0600, masked on read), tenants add/list, metrics add/list. Everything web-configurable. |

Rule: one running cycle max. Finish returns `produced_version` (vN+1) and rewrites `version.json`.

## Architecture

```
server/app.py    stdlib only: static public/ + /api/cycles /api/version /api/cycle/start /api/cycle/finish /api/admin/reload
public/index.html  single-file UI, mobile-first, 10s refresh
needs.json       ALL machine values: port, bind, paths
version.json     current version (bumped by finish)
SUCCESS.md       owner success bar: margin > costs incl AI, above niche avg
data/config.overrides.json  web-saved config (wins over needs.json)
data/secrets.json  MoR API key only, chmod 600, never echoed
data/tenants.jsonl data/metrics.jsonl  tenants + revenue/cost periods
data/cycles.jsonl  append-only cycle log
bin/serve.sh     start/stop + live URL report
bin/cycle.sh     one full agent cycle from CLI: start -> work -> finish
test/check.sh    API + first-paint smoke
```

## The continuous loop (each leg)

1. Read `/api/cycles` + `/api/version` — what is running, what is latest.
2. If a cycle is `running` and stale, finish or replace it. Else start one with a small goal.
3. Do the smallest work that earns a version bump. No roadmaps.
4. `finish` with notes → `version.json` bumps → visible on board.
5. Append one improvement idea to `IDEAS.md` (owner law). Exit.

## Run

```bash
bash bin/serve.sh            # start + URL report
bash bin/cycle.sh "goal" "notes"   # one full cycle
bash test/check.sh
```

## DONE ladder

1. WORKING — :8339 serves board, start→finish bumps v1→v2, check.sh PASS.
2. DEPLOYED — tailnet URL, survives reboot.
3. TESTED — e2e per leg (finish always bumps, double-start 409).
4. ANNOUNCED — owner ping with URL.
5. MONETIZED — MoR key pasted in Admin after owner KYC; paywall only after usage proof. Margin tracked in Admin → Metrics, target 40% vs niche 25% (see SUCCESS.md).
