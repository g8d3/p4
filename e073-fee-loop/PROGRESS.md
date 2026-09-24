# PROGRESS — the check-in board (owner standing order: every review shows movement)

Standing order (2026-09-24): keep working — session or dispatcher — so that
every owner review finds progress. Progress = settled bets / dead assumptions,
never tick counts. This file is the single place to check.

## M1: 10 strangers, paid actions, 30 days — $1,000 budget

- Status: DESIGNED, not started. Needs: referral page + action menu + payouts.
- Pass: >=10 strangers complete a paid action by day 30.
- Kill: <10 → incentive design dead, directory survives as plain product.

## Live systems

| system | state | last change |
|---|---|---|
| fee dispatcher (`bin/chain.sh`) | ALIVE, completion-chained | epochs ticking back-to-back (see `history.jsonl`) |
| town registration (`e072/bin/register.sh`) | knocking, town throttling newcomers | try count grows in `e072/log/register.log` |
| owner wallet signature | WAITING on human | needed after registration (`ownerUrl`) |

## Tables tended

| table | rows | movement |
|---|---|---|
| `seeds/agent-worlds.csv` | 4 worlds, all unregistered | Clanker Town row flips on registration |
| `seeds/mor-directory.csv` | 11 MoRs (owner sheet) | awaiting freshness leg |
| `seeds/contrib-repos.csv` | 1 (pi-web scouted: setup 1 min, no CLA) | scout legs add rows + fill columns |

## Architecture (locked)

- Fees: 1% ceiling, dynamic by contribution; split 30 platform / 70 promoter pool.
- Sinks: 60 burn / 25 POL / 15 contributors, single weekly multisend. No staking yield.
- Bond: stake = utility key + slashable collateral. Discounts for both roles.
- Cold start: useful thing → paid actions in stables → token last, backed by flow.
- Registry vision: onchain agent registry, plural gateways, results as attestations.

## Known issues (honest)

- Fee fitness flat since epoch 1 (best 286): toy model needs diversity guard + stronger mutation.
- `history.jsonl` grows unbounded: needs compaction before it becomes noise.
- `e072` was a stub; registration is the first real-world proof in flight.

## Leg log (newest first)

- 2026-09-24 leg: town-first-post-3 re-verified (fresh poll cursor 369/376: #1 still 1 rating Mossy Turbine mixed 3/4 on-topic 0 replies, #2 0/0, no Mossy follow-up so no reply owed; #3 msg_mufqzcq04047yt1w2 seq 3960 live in cafe-cumulus, no duplicate re-post) → runs/town-first-post-3.md.
- 2026-09-24 leg: town-first-post-3 done (polled #1: 1 rating Mossy Turbine mixed 3/4 on-topic, 0 replies; #2: 0 ratings 0 replies; no Mossy follow-up so no reply owed; position #3 staking-as-bond 443/500 chars spoken in cafe-cumulus, town ok:true msg_mufqzcq04047yt1w2 seq 3960, 24 recipients) → runs/town-first-post-3.md.

- 2026-09-24 leg: town-first-post-2 done (polled msg_mufqi86wby8gfxm8: 1 rating Mossy Turbine mixed 3/4 on-topic, 0 replies; position #2 promoter-rebate 428/500 chars spoken in cafe-cumulus, town ok:true msg_mufqvz8r3ci8hd6qy seq 3285, 24 recipients) → runs/town-first-post-2.md.
- 2026-09-24 leg: town-first-post-1 done (position #1 dynamic-vs-flat 444/500 chars spoken in cafe-cumulus Debate Diner, town ok:true msg_mufqi86wby8gfxm8 seq 288, 24 recipients) → runs/town-first-post-1.md.
- 2026-09-24 leg: town-debate-prep done (3 venue-ready positions <=500 chars: dynamic-vs-flat, promoter-set rebate, staking-as-bond, each w/ steelman counter) → runs/debate-prep.md.
- 2026-09-24 leg: mor-fresh-1 done (11/11 homepages HTTP 200 via curl, Gumroad fixed 0.3→0.5 USD verified on /pricing, Paddle/Lemon/Dodo/Creem fees confirmed, rest untouched, checked_at stamped) → mor-directory.csv +3 cols.
- 2026-09-24 leg: contrib-sweep-1 done (+5 agent-tooling rows w/ open good-first-issues, all GitHub-API verified, scout cols empty) → contrib-repos.csv now 6 rows.
- 2026-09-24 leg: FIRST LLM LEG DONE (muse-spark-1.3-contributor): contrib-sweep-1 added 5 verified rows (autogen, AutoGPT, crewAI, langfuse, Flowise) → 6 repos; queue popped; spend logged. Town worker hit 120-try cap, restarted unbounded. Credit meter live: $0.95/7d measured locally, no API.
- 2026-09-24 leg: pi-web scout done (clone+install+build 6s, MIT, no CLA, 5 open issues) → contrib row filled; PROGRESS.md created; town try ~39 still throttled; fee chain alive.
- 2026-09-24 leg: demand-probe-1 done (11 products ranked by outside-want evidence: #1 e042-bk2 38 members/76 credits/721 purchases real workbook data, rest no outside users, stars/town/search empty) → runs/demand-probe-1.md.
- 2026-09-24 leg: e042-meet-prep-1 done (recon only: app boots 200, /api/report matches banco.db 38/76/61, exports+preview 200, unauth 401; BLOCKER funnel URL 502 proxying wrong port, valorizations 0 rows, previews 0 income, box negative → next action re-run ./funnel.sh) → runs/e042-meet-prep-1.md.
- 2026-09-24 leg: e042-funnel-fix-1 done (reset stale 3071 mapping, re-ran ./funnel.sh → public URL 200 byte-identical to local 9091, PIN login screen present, public /api/report unauth 401; db re-verified 38/76/61, e042 untouched) → runs/e042-funnel-fix-1.md.
- 2026-09-24 leg: e042-meet-send-1 done (1-line PIN strip in e042-bk2/app.py committed 92a4e5e, app rebooted: authed overview/report settings 5 keys pin_present=False, login ok, 38 members/76 credits intact; public URL 200 39491B identical to local, PIN screen present, public /api/report 401; send staged for owner forward, open-confirm pending, meeting date empty) → runs/e042-meet-send-1.md.

## KILLED 2026-09-24: Clanker Town line (owner order)
- Reason: needs a human login with no clear instructions. Anything needing a human action to proceed is dead weight for this system.
- Town legs stop. Effort moves to e042-bk2 (real users, reachable now).
- 2026-09-24 leg: e042-valoriza-1 done (read-only preview: 61 payments interest 0.0 + 721 purchases 15218 shares → 2026-08 close previews profit 0/delta 0/new_value 10000, all 38 gains 0.0, valorizations still 0 rows, commit SQL staged not run) → runs/e042-valoriza-1.md.
