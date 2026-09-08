# e054 PLAYBOOK — how to run agent bounty hunts efficiently

Distilled from this session's data (round 1: 63 sweeps, 1 bounty PR merged-candidate, CI iterations, trust-gate pass). Read this before any new hunt run — it is the efficiency loop: every round appends what it learned.

## The pipeline that worked (with measured costs)

| Phase | What | Cost this session | Yield |
|---|---|---|---|
| 0. Recon | Find live, real money routes. Reject honeypots. | ~15 min | 1 route (Turso $1k/bug) |
| 1. Infra | Clone + build `limbo_sim`/whopper, smoke-test one seed | ~5 min | working harness |
| 2. Sweep | 11 workers × `-t 60..120`, varied profiles | ~3 h | 41 failures → 1 real lead |
| 3. Triage | Artifacts vs engine bugs (the 90% vs 10% rule) | ~30 min | seed 3903403 → issue #6774 |
| 4. Verify | Port test to main, watch it fail; re-run on branch, watch it pass | ~15 min | independent confirmation |
| 5. Fix+test | Minimal diff, regression tests | ~1 h (agent) | branch ready |
| 6. Ship | Fork → push → PR with disclosure → survive trust gate → iterate CI | ~40 min | PR #8812, 164 checks green |

**Lesson: triage is where rounds are won.** 41 of 63 sweep failures were artifacts (time-cap, shrink noise, simulator-infra panics, MVCC header false positives). One real lead paid for the whole farm.

## Recon map (as of Sep 2026)

- **Turso Challenge** — the only live Algora challenge. $1,000 per data-loss/corruption bug; smaller for wrong-results. Leaderboard proves recurring payouts. DST (limbo_sim) + concurrent (whopper) + differential modes = three different bug classes from one repo. **Richest known vein.**
- Algora pivoted to recruiting — all other challenges "Completed". Per-org `/tip` still exists (see payment rails).
- GitHub search "bounty" label = honeypot swarm (fake repos, invented tokens, 11k-issue farms). Filter: real repos have org backing, merged-bounty history, and maintainer `/tip` comments on old PRs. Verify a repo paid someone before working its "bounties".
- Watch: Polar.sh bounties, new Algora challenges page, Turso leaderboard growth (new payouts = fresh confidence).

## Hunt recipes by bug class

- **Corruption/data-loss**: `limbo_sim` write-heavy profiles + `PRAGMA integrity_check` cross-check against stock SQLite via rusqlite on a checkpointed file. Winning pattern from leaderboard: extend simulator coverage + failing seed + minimal fix.
- **Wrong-results**: `--differential` mode (compares vs real SQLite). Cheaper to reproduce than corruption; usually smaller bounty but easier merges.
- **Crash-recovery**: whopper multiprocess+kill. Chaos = hard minimization; budget extra time, aim to reduce kill-chaos to deterministic steps (targeted kill -9 at state-machine boundaries).
- Known artifact signatures (do NOT chase): time-cap/shrink failures, ATTACH-lock simulator panics, `Version::Mvcc=255` header false positives, layout-fragile page_count assertions across platforms (macOS vs Linux b-tree splits differ!).

## Verification gates (never skip, never trust the child)

1. Port the regression test onto `main` — watch it FAIL.
2. Run on the fix branch — watch it PASS.
3. `cargo fmt --check` BEFORE pushing (CI gate #1).
4. Tests must be layout-robust (no exact page-count assertions from fragile growth sequences).
5. Attribute every CI failure: is it reachable from my diff? (guard analysis: e.g. code under `AutoVacuumMode::Full` cannot break non-autovacuum workloads). Post the analysis + failure seeds as a PR comment — turns flakes into goodwill.

## PR etiquette that passed Turso's gates

- Trust gate scores accounts (prior_interaction weight 0.24, commit_email, verification). Aged account + noreply email + clean PR body passed. Prior AI PRs were DENIED pre-gate for low trust — an established account matters more than anything else.
- The template REQUIRES a "Description of AI Usage" section — disclose harness, model, supervision. AI use is explicitly encouraged; hiding it is the reputation risk.
- Commit style: `[scope: ]lowercase imperative` + why-body + `Tests:` + `Fixes #N`. No Conventional-Commit prefixes needed. No logic+formatting mixing.
- Check "allow edits from maintainers". Keep PRs small; split follow-ups (PR2) rather than inflating.
- CI pitfall map: fmt → run it locally first; macOS → layout-fragility; IOUring sim jobs → flaky, their own shrinker may fail to reproduce; whopper multiprocess-kill → rare FTS flakes (seed documented).

## Payment rails (verified end-to-end on merged bounty PR #6626)

1. PR merged (maintainer reviews; response latency matters — watchtower running).
2. Maintainer comments `/tip @user $1000`.
3. `algora-pbc[bot]` posts a Stripe claim link bound to the GitHub account.
4. **Human-only step**: claim via Stripe with the GitHub login. Agent cannot and should not do this.

## Round-over-round loop (the efficiency multiplier)

1. After each round: append new artifact signatures, CI pitfalls, and timing data HERE (not in chat history).
2. Keep `bugs/` (failing-seed DBs) — they are re-verification gold when upstream moves.
3. Re-verify parked leads against fresh `main` before investing (bugs die by merge).
4. Watch the leaderboard: new payout entries reveal what maintainer currently rewards.
5. Parallelize with isolated clones (`git clone --shared`), one child per route, single-writer rule per clone, CPU budgets stated in each prompt.

## Round-3 additions (Sep 8)

- **Targeted hunts beat sweeps for round 3+**: upstream issues with maintainer
  engagement ("does this still reproduce?"), no assignee, no linked PRs are
  the highest-EV targets — the triage is half-done for you and a merged fix
  answers a direct ask. (#8197 → PR #8844 in ~80 min end-to-end.)
- **Re-check `git diff --name-only main origin/main` before investing**: bugs
  die by merge; subsystems untouched upstream keep parked PRs valid (the 22
  new commits left pager/wal/btree alone → #8812/#8819 still mergeable).
- **Push quirk**: branches rebased on fresh main that carry upstream
  workflow-file commits cannot push over a workflow-scope-less https PAT
  (GitHub refuses). Keep the SSH remote configured (`git@github.com:...`) as
  fallback; `gh auth` https + SSH coexist fine.
- **Disk discipline**: 229G volume hit 100% mid-CI (rust incremental caches
  7G + classified-FP bug artifacts 1.3G). Prune `target/debug/incremental`
  per clone and `bugs/farm-s*` artifacts once a round's triage classifies
  them as false positives. Keep only confirmed-bug DBs.
- **CI status mapping in watchtower**: mergeStateStatus UNKNOWN/UNSTABLE right
  after push = checks still running; only CLEAN/PENDING-with-reviews matters.
