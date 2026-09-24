# demand-probe-1 — Find what to sell (2026-09-24)

Probe of the 11 runnable web products. Ranked by evidence of **outside want**
(real users, traffic, money, town demand). Rule: every cell below comes from a
command run on 2026-09-24 (nested `git log`, `sqlite3` counts, file reads,
`ss`, `grep` over `e072` log) or stays empty. No invented numbers. No keys in
this file (one product has a hardcoded key; value redacted, flagged only).

## Ranked table (one fact per column)

| rank | experiment | runnable_entry | outside_users_count | outside_users_who | traffic_signal | money_signal | commit_activity | checked_at |
|---|---|---|---|---|---|---|---|---|
| 1 | e042-bk2 (Banco Comunal) | app.py (uvicorn :9091) | 38 | dad's BANKOMUNAL MANOS UNIDAS members (bk.txt diary = direct feature request) | Tailscale Funnel URL shipped (PIN-gated); no hit counter found | 76 credits, 61 payments, 721 share purchases in banco.db (imported from real bk-book.xlsx) | 6 (nested git log) | 2026-09-24 |
| 2 | e058-funding-scanner | app.py | empty | empty | no public URL found; server.log shows local runs only | paper only: 251 paper_calls, 186 paper_outcomes, 3,376,941 funding rows; paper hit-rate below 55% propose bar (stays PAPER) | 96 | 2026-09-24 |
| 3 | e060-social-memecoin-radar | app.py (:8323 tailnet, DEPLOYED.md rung 2+3) | empty | empty | tailnet URL + /health verified 2026-09-12 per DEPLOYED.md; none live on probe (`ss` shows :8323 down) | paper only: 25 resolved, 8 hits, 32.0% hit rate, 147 pending (paper/score.json 2026-09-15) | 89 | 2026-09-24 |
| 4 | e045-gmgn-clone | app.py (:8338 per bin/run.sh) | empty | empty | no public URL; 10 screenshots banked in data/ ( REAL-data terminal, free APIs) | empty (no billing, no referrals wired) | 1 | 2026-09-24 |
| 5 | e008-asistente-ht | server.js (:3000) | 3 | 3 named HT profiles (Pedro Juan Criollo, Victor Cortes, Product Team PDFs = source material, not confirmed paying users) | localhost only (server.log shows local boot); no public URL | empty | 4 (nested git log) | 2026-09-24 |
| 6 | e048-storyo | server.js (:8180, proxy infiniteslop.ai) | empty | empty | no live listener on probe; clone/ mirror banked (68KB HTML + hls.min.js) | concept-only ladder (L1 ~$0.025/s cited in AGENTS.md, unverified spend) | 1 | 2026-09-24 |
| 7 | e047-chair-studio | server.js (:5190) + index.html | empty | empty | localhost only; no public URL | empty (marketplace packs are DESIGN.md future, not built) | 1 | 2026-09-24 |
| 8 | e046-kaplay-game | index.html (Vite dist/ built) | empty | empty | dist/ build present; embeds into e061 via postMessage; no player count | empty | 2 | 2026-09-24 |
| 9 | e062-agent-ops | app.py | empty (internal: 168 runs, 1790 events, 12 heartbeats in ops.db = agent legs, not strangers) | empty | no public URL; internal ops board | BUSINESS.md doctrine only (no billing live) | 101 | 2026-09-24 |
| 10 | e063-fleet-ui | app.py | empty (internal reskin of e062 ops.db board) | empty | no public URL | empty | 8 | 2026-09-24 |
| 11 | e067-sys-panel | app.py (:8326) | empty (internal: ports/cron/systemd panel) | empty | localhost only on probe | empty | 2 | 2026-09-24 |

## Columns with zero signal everywhere (honest empties)

- stars: none of the 11 are published public repos (nested .git in e008/e042, all others p4-local). Empty, not zero-claimed.
- town demand: `grep -ci` over e072 register.log for product names = 0 mentions.
- search demand: no search-console / analytics access from this leg; left empty rather than invented.

## Evidence ledger (command → fact)

- `git -C e008 log --oneline | wc -l` = 4; `git -C e042` = 6; p4 `git log --oneline -- <dir> | wc -l` = e045:1, e046:2, e047:1, e048:1, e058:96, e060:89, e062:101, e063:8, e067:2.
- `sqlite3 e042 banco.db`: members 38, credits 76, payments 61, purchases 721, valorizations 0 (month-close never run in app).
- `sqlite3 e058 data.db`: funding 3376941, signals 117, paper_calls 251, paper_outcomes 186.
- `e060/paper/score.json` (2026-09-15): resolved 25, hits 8, 32.0%; pending 147; `wc -l calls.jsonl` = 39.
- `sqlite3 e062 ops.db`: runs 168, events 1790, heartbeats 12.
- `ss -tln`: none of :3000/:8180/:8323/:8326/:8338/:9091 listening at probe time.
- Hygiene flag (no value quoted): e008 server.js ships a hardcoded API key fallback — rotate before any sale/share.

## Most sellable next step for #1 (e042, exactly one)

Run the next real monthly meeting inside the app: dad records that month's
payments + grants one distribution credit + closes valorizacion (currently 0
rows) on the live Funnel URL, with the leg watching server.log. Success = the
meeting sheet the bank already trusts comes out of `/api/report` instead of
Excel. That converts the only product with named waiting users into M1's first
stranger-paid-action shape; everything else on the list has no outside user to
close.
