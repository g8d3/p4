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

- 2026-09-24 leg: contrib-sweep-1 done (+5 agent-tooling rows w/ open good-first-issues, all GitHub-API verified, scout cols empty) → contrib-repos.csv now 6 rows.
- 2026-09-24 leg: FIRST LLM LEG DONE (muse-spark-1.3-contributor): contrib-sweep-1 added 5 verified rows (autogen, AutoGPT, crewAI, langfuse, Flowise) → 6 repos; queue popped; spend logged. Town worker hit 120-try cap, restarted unbounded. Credit meter live: $0.95/7d measured locally, no API.
- 2026-09-24 leg: pi-web scout done (clone+install+build 6s, MIT, no CLA, 5 open issues) → contrib row filled; PROGRESS.md created; town try ~39 still throttled; fee chain alive.
