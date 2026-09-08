# e055-agent-bounty-marketplace

**Idea (proposed by the user, Sep 2026, born from e054):** a web application where anyone can point an agent at real money rewards — OSS bounties, DST bug challenges, tips — and the pipeline this repo proved (recon → hunt → verify → PR → claim) runs as a product.

## Why it could work (evidence from e054)

- The full loop was executed end-to-end by one agent in ~5 h: live recon, fuzzing farm, verified fix, compliant PR (164 green checks), trust-gate pass.
- The scarce resources are: trusted accounts (trust gates score account age/history), fuzzing CPU-hours, and review-latency discipline — all poolable behind a product.
- Precedent platforms: Algora (tips/bounties + hiring), Polar. None offer "bring your agent" as the worker.

## Product sketch

1. **Submit a target**: repo + bounty URL (Turso Challenge, any `/tip` org, Polar bounty).
2. **Agent runs the PLAYBOOK pipeline** (see `../e054-money-agent/PLAYBOOK.md`): clone, sweep, triage, verify, PR with AI disclosure from the USER's GitHub account (their trust score, their reputation — aligned incentives).
3. **Human-in-the-loop gates**: PR open (user approves), review response (user or agent drafts), payment claim (user's Stripe via Algora).
4. **Revenue**: % of claimed bounties, or subscription for the farm (CPU-hours) + watchtower (review-latency SLO).

## Hard problems (honest list)

- Trust gates are account-bound: scaling means many users' accounts, each vouching their own agent runs. Reputation design is the core product problem.
- Liability: agent-authored PRs to third-party repos at scale will attract repo-side anti-agent gates (Turso already auto-closes low-trust PRs).
- Bug duplication: first-solver-wins markets need fast global dedup of in-flight hunts.

## Status

Idea registered. Do not build until e054 round 2 results validate unit economics (bounties claimed / CPU-hour). Next concrete step: if PR #8812 merges and pays, write the landing page and run ONE external user through the pipeline manually ("concierge MVP").
