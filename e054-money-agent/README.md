# e054-money-agent

Replication of the "Astra made me money" experiment (X post by @bil0090, Sep 2026):
give a coding agent one goal — *go make real money* — and see how far it gets without human help.

## Target found (live recon, Sep 7 2026)

Scanned real money routes: Algora pivoted to recruiting; all its challenges are completed except one:

- **Turso Challenge** — https://algora.io/challenges/turso — **$1,000** per bug causing
  data loss/corruption in Turso (Rust SQLite rewrite), leaderboard shows recent $800–$2,500 payouts.
  Perfectly agent-suited: deterministic simulation testing (DST) at scale.

Honeypot alert: GitHub search surfaces dozens of fake "bounty" repos aimed at agent farms
(11k-issue `bug-bounty` repos, bounties paid in invented tokens). Skipped.

## Payment rail (verified on merged bounty PR #6626)

1. Agent finds bug → opens PR → maintainer merges.
2. Maintainer comments `/tip @user $1000`.
3. `algora-pbc[bot]` posts a Stripe claim link (GitHub OAuth).
4. Only human-gated step: claim payout with the GitHub account's Algora/Stripe session.

## Structure

- `turso/` — shallow clone of tursodatabase/turso (the hunting ground)
- `results/` — simulator sweep logs
- `bugs/` — confirmed failure artifacts per seed
- `FINDINGS.md` — the hunt log (primary deliverable besides any branch)

## Status

- Subsession running mass seed sweeps (`limbo_sim` + Whopper concurrent DST) on 12 cores.
- Gate before any PR: bug must reproduce on current `main`, be novel (issue/PR triage),
  and be minimized with a regression test.

## Round 2 (in flight, Sep 8 2026)

- `hunt/fts-crash` — suspected FTS index data-loss across crash recovery (seed 7399741717491843615) → possible PR #2.
- `work-farm` — fresh sweeps (seeds 20M+, differential mode) + MVCC stale-read lead verification (seed 3698380).
- `work-pr2` — PR2 prep: full ptrmap coverage branch (local only, ships after PR1 review feedback).
- `watchtower.sh` — polls PR #8812 every 5 min, alerts on reviews/state changes (24 h lifetime).
- `PLAYBOOK.md` — session-data efficiency loop: recipes, costs, gates, PR etiquette, payment rails.
- Idea spun out: `../e055-agent-bounty-marketplace/` (user's concept — the pipeline as a product).

## Round 3 (Sep 8, day session)

- **Bug #3 verified + fixed**: upstream #8197 (MVCC read-your-own-write, in-btree cursor).
  Regression test fails on fresh `main` (`c83cac5e0`), passes with a +31-line read-path fix.
  Shipped: verification comment on #8197 + **PR #8844** (Fixes #8197, maintainer-edits on, AI disclosed).
- Upstream `main` +22 commits: none touch pager/wal/btree → PRs #8812/#8819 still valid.
- watchtower v3: watches ALL THREE PRs (#8812, #8819, #8844).
- Farm round 3: 36 jobs, seeds 40M–60M, `-t 300..600`, 6 slots, per round-2 recipe.
