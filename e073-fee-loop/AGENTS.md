# e073 — Fee Loop (evolutionary fee genomes, paper first)

Agents breed the fee schedule. Humans hold only the timelock key.

## Idea (from owner sessions 2026-09)

- 1% fee is a ceiling, not flat: contributors pay less (volume, generosity, builder, stake).
- Referral split: 30% platform / 70% promoter pool; promoter sets `rebatePct` to referrals.
- Sinks of platform share: POL / staking rewards / buy-and-burn (start 40/40/20).
- N fee genomes compete per epoch; fitness elects the winner; winner mutates into challengers.

## Fitness (one number, hard to game)

```
fitness = retainedVolume * (1 - washRate) * retention30d
```

Never raw volume, TVL, or trader count alone.

## Files

- `genomes.json` — live genomes (champion + challengers). The fee genome is config, not code.
- `loop.py` — one paper epoch: simulate traders choosing universes by net fee,
  compute fitness, print leaderboard, append to `history.jsonl`.
- `history.jsonl` — one row per genome per epoch (paper model v0, deterministic seed).
- `bin/epoch.sh` — run one epoch + promote winner (paper: rewrite `genomes.json`).
- `AGENTS.md` — this file.

## Model v0 (paper only, honest toy)

Traders pick the universe with the lowest net fee via logit choice.
Net fee = effectiveFee − rebate. Retention rises with rebate + low fee.
Wash rises with rebate, falls with stake weight (tradeoff is real:
generosity attracts both keepers and farmers).

## Promotion rules

- Champion keeps 80% traffic, challengers split 20% (real epochs).
- Challenger promotes only after beating champion 2 epochs in a row.
- Paper epochs: daily, free. Real epochs (e052): weekly, timelocked.
- Mainnet promotion: multisig + timelock, humans can veto, silence = approval.

## Run

```bash
cd e073-fee-loop
python3 loop.py            # simulate one epoch, print leaderboard
bash bin/epoch.sh         # simulate + promote winner with 2 mutants
```

## Seeds (tables the chain tends)

- `seeds/mor-directory.csv` — merchant-of-record directory (owner's sheet, 11 rows).
- `seeds/agent-worlds.csv` — agent-world directory (4 rows, all `our_status=unregistered`).

## Table doctrine (owner law)

Tables update rows AND columns, continuously, via chain legs:

- Row legs integrate new sources (new worlds, new MoRs, new numbers).
- Column legs split mush: any column mixing two facts ("fee 5% + $0.5" in
  one cell, "Base / open" in one cell) is split into typed columns so every
  column filters, sorts, and analyzes cleanly. One fact per column.
- Freshness legs stamp `checked_at` and downgrade stale cells, never delete.
- Chain legs (planned): row-adder, column-splitter, freshness-checker —
  picked per tick by stalest need, not by rotation.

## Status

- Epoch 1: paper, 3 genomes, model v0. See `history.jsonl`.
