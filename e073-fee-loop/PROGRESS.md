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

- 2026-09-24 ASK owner (blocked, eighth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1751 metered total (45 rows). Referral hook + one-click decide + paid-action menu all live; only outside send (human WhatsApp relay) moves this. Dad line at ~12 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands.

- 2026-09-24 ASK owner (blocked, seventh ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1718 metered total (44 rows). Referral hook + one-click decide + paid-action menu all live; only outside send (human WhatsApp relay) moves this. Dad line at ~11 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — further polls or builder legs without first stranger contact are paper ticks by prior ruling.
- 2026-09-24 ASK owner (blocked, sixth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1700 metered total (43 rows), local root 200 46760B (paid-action menu still live). Referral hook + one-click decide + paid-action menu (copia-extracto $5000, paz-y-salvo $10000) all live; only outside send (human WhatsApp relay) moves this, another poll or builder leg without first stranger contact would be a paper tick. Dad line at ~10 legs, far below 100-try kill rule, so line stays alive and nothing is queued.

- 2026-09-24 ASK owner (blocked, fifth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1676 metered total (42 rows). Referral hook + one-click decide + paid-action menu (copia-extracto $5000, paz-y-salvo $10000) all live; only outside send (human WhatsApp relay) moves this, another poll would be a paper tick. Dad line at ~9 legs, far below 100-try kill rule, so line stays alive and nothing is queued.

- 2026-09-24 leg: e042-action-menu-2 done (paid-action menu live: 2 priced actions copia-extracto $5000 + paz-y-salvo $10000, auth-exempt POST /api/action → runs/e042-actions.jsonl, one-click buttons on PIN screen + Inicio no login, local+public 200 byte-identical 46760B with 8 menu markers, test POSTs round-tripped local+public then removed, bad action 400, /api/report 401 both doors, banco.db mtime+md5 unchanged, valorizations 0 rows, real actions PENDING) → runs/e042-action-menu-2.md.

- 2026-09-24 leg: e042-action-menu-1 NOT DONE docs-only (paid-action menu absent: local+public 200 byte-identical 44940B with 0 menu markers, POST /api/action + /api/actions 401 no endpoint, runs/e042-actions.jsonl absent 0 rows, /api/report 401 both doors, banco.db mtime+md5 unchanged, valorizations 0 rows; builder leg still needs app.py + index.html) → runs/e042-action-menu-1.md.

- 2026-09-24 ASK owner (blocked, fourth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.145 metered total (37 rows). Referral hook + one-click decide + in-app ask all live; only outside send (human WhatsApp relay) moves this, another poll would be a paper tick. Dad line at ~8 legs, far below 100-try kill rule, so line stays alive and nothing is queued.

- 2026-09-24 ASK owner (blocked, third ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1424 metered total (33 rows). Referral hook + one-click decide + in-app ask all live and byte-identical local/public; only outside send (human WhatsApp relay) moves this. Dad line at ~8 legs, far below 100-try kill rule, so line stays alive and nothing is queued.

- 2026-09-24 ASK owner (still blocked, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 rows, runs/e042-decisions.jsonl 0 rows, LEG_QUEUE empty, spend pace ~$0.14 metered total. No outside send on record; another poll would be a paper tick.

- 2026-09-24 ASK owner: forward runs/e042-dad-forward-2026-08.txt + the public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS (one click, PIN screen, no login); reply with his word. Unblocks August close (valorizations 0 rows → profit 58050 / action 10003.81) → member-gains story → M1 referrals. 6 legs staged with zero outside send; no further worker leg until reply lands. Referral hook live, first stranger row still PENDING.

- 2026-09-24 leg: e042-referral-1 done (M1 referral hook live: PIN-screen + Inicio forms POST /api/refer → runs/e042-referrals.jsonl, local+public 200 byte-identical 44940B, test referrals round-tripped local+public then removed, blank name 400, banco.db mtime+md5 unchanged, valorizations 0 rows, real referrals PENDING) → runs/e042-referral-1.md.

- 2026-09-24 leg: e042-decide-click-1 done (one-click APRUEBO/ESPERAMOS live: PIN-screen + Inicio buttons POST /api/decide → runs/e042-decisions.jsonl, local+public 200 byte-identical 4 buttons, test clicks round-tripped local+public then removed, bad value 400, banco.db mtime+md5 unchanged, valorizations 0 rows, dad reply PENDING) → runs/e042-decide-click-1.md.

- 2026-09-24 leg: e042-inapp-ask-1 done (read-only August-close ask live in app: PIN-screen + Inicio notice with before 10000.00/0/0-rows vs after 58050/10003.81, APRUEBO/ESPERAMOS line; local+public 200 41302B identical, /api/report 401 both doors, valorizations 0 rows, zero DB writes) → runs/e042-inapp-ask-1.md.

- 2026-09-24 leg: e042-dad-deliver-1 done (no outside-repo send by this leg, reply PENDING — forward still staged, live re-verified valorizations 0 rows + preview 10000.00 + public URL 200 39491B + report 401, gate restated) → runs/e042-dad-deliver-1.md.

- 2026-09-24 leg: e042-dad-check-1 done (no APRUEBO/ESPERAMOS reply on record — forward text only; re-verified live valorizations 0 rows + live preview 10000.00 + public URL 200 39491B + report 401 unauth, gate restated) → runs/e042-dad-check-1.md.

- 2026-09-24 leg: e042-dad-send-1 done (copy app 9095 split+close: live preview 10000.00 vs copy 10003.81 both via HTTP, report 10000.0→10003.81, public URL 200 39491B + report 401, live valorizations still 0 rows, forward staged) → runs/e042-dad-send-1.md + runs/e042-dad-forward-2026-08.txt.

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

- 2026-09-24 leg: e042-close-pack-1 done (copy-DB split 61/61 verified: 2026-08 interests 64500/profit 58050/delta 3.81/new_value 10003.81 matches interest-split-1, live-run SQL + 5-line Spanish forward staged for dad approve/deny, live valorizations still 0 rows) → runs/e042-close-pack-1.md.
- 2026-09-24 leg: e042-interest-split-1 done (read-only 3%-on-balance recompute over 61 payments: every credit paid once so due=amount*3%; all 10 months >0, 2026-08 pay 20 → interest_pronto 64500.0/diezmo 6450.0/profit 58050.0/delta 3.81/new_value 10003.81 on 15218 shares, stored interest still 0.0 so no commit) → runs/e042-interest-split-1.md.

## KILLED 2026-09-24: Clanker Town line (owner order)
- Reason: needs a human login with no clear instructions. Anything needing a human action to proceed is dead weight for this system.
- Town legs stop. Effort moves to e042-bk2 (real users, reachable now).
- 2026-09-24 leg: e042-valoriza-1 done (read-only preview: 61 payments interest 0.0 + 721 purchases 15218 shares → 2026-08 close previews profit 0/delta 0/new_value 10000, all 38 gains 0.0, valorizations still 0 rows, commit SQL staged not run) → runs/e042-valoriza-1.md.

- 2026-09-24 ASK owner (blocked, ninth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1769 metered total (46 rows). Referral hook + one-click decide + paid-action menu all live; only outside send (human WhatsApp relay) moves this. Dad line at ~13 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands.

- 2026-09-24 ASK owner (blocked, eleventh ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1811 metered total (42 metered of 48 rows). Referral hook + one-click decide + paid-action menu all live; only outside send (human WhatsApp relay) moves this. Dad line at ~15 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — each re-invocation burns ~$0.002 with zero movement.

- 2026-09-24 ASK owner (blocked, tenth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1791 metered total (47 rows). Referral hook + one-click decide + paid-action menu all live; only outside send (human WhatsApp relay) moves this. Dad line at ~14 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — each re-invocation burns ~$0.002 with zero movement.

- 2026-09-24 ASK owner (blocked, twelfth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1827 metered total (49 rows). Full funnel live; only outside send (human WhatsApp relay) moves this. Dad line at ~16 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — each re-invocation burns ~$0.002 with zero movement.

- 2026-09-24 ASK owner (blocked, thirteenth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1843 metered total (50 rows). Full funnel live; only outside send (human WhatsApp relay) moves this. Dad line at ~17 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — each re-invocation burns ~$0.002 with zero movement.

- 2026-09-24 ASK owner (blocked, fourteenth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1868 metered total (45 metered of 51 rows). Full funnel live; only outside send (human WhatsApp relay) moves this. Dad line at ~18 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — each re-invocation burns ~$0.002 with zero movement.

- 2026-09-24 ASK owner (blocked, fifteenth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1888 metered total (46 metered of 52 rows). Full funnel live (referral hook + one-click decide + paid-action menu, local+public byte-identical per runs/e042-action-menu-2.md); only outside send (human WhatsApp relay) moves this. Dad line at ~19 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — each re-invocation burns ~$0.002 with zero movement.

- 2026-09-24 ASK owner (blocked, sixteenth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1916 metered total (47 metered of 53 rows). Full funnel live (referral hook + one-click decide + paid-action menu, local+public byte-identical per runs/e042-action-menu-2.md); only outside send (human WhatsApp relay) moves this. Dad line at ~20 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — each re-invocation burns ~$0.002 with zero movement.

- 2026-09-24 ASK owner (blocked, seventeenth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1934 metered total (48 metered of 54 rows). Full funnel live (referral hook + one-click decide + paid-action menu, local+public byte-identical per runs/e042-action-menu-2.md); only outside send (human WhatsApp relay) moves this. Dad line at ~21 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — each re-invocation burns ~$0.002 with zero movement.

- 2026-09-24 ASK owner (blocked, eighteenth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.196 metered total (49 metered of 55 rows). Full funnel live (referral hook + one-click decide + paid-action menu, local+public byte-identical per runs/e042-action-menu-2.md); only outside send (human WhatsApp relay) moves this. Dad line at ~22 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — each re-invocation burns ~$0.002 with zero movement.

- 2026-09-24 ASK owner (blocked, nineteenth ask, no worker leg queued): forward runs/e042-dad-forward-2026-08.txt + public app URL to dad (WhatsApp), have him open it and tap APRUEBO or ESPERAMOS; reply with his word. Re-verified 2026-09-24: runs/e042-referrals.jsonl 0 bytes, runs/e042-decisions.jsonl 0 bytes, runs/e042-actions.jsonl 0 bytes, LEG_QUEUE empty (0 bytes), spend pace $0.1987 metered total (50 metered of 56 rows). Full funnel live (referral hook + one-click decide + paid-action menu, local+public byte-identical per runs/e042-action-menu-2.md); only outside send (human WhatsApp relay) moves this. Dad line at ~23 legs, far below 100-try kill rule, so line stays alive. SPEND GUARD: dispatcher should not re-invoke decider/worker legs until this reply lands — each re-invocation burns ~$0.002 with zero movement.
