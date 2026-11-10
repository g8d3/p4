# e109 — AI miner network (mine the results, pay for the network, small profit over cost)

**The proposal (owner, 2026-11-10)**: launch a blockchain where people mine AI results — the
business-owner workflows of e108 — and participants only pay for the network, receiving a small
profit over their cost.

**Verdict: build the market, not the chain.** Everything the chain would add (settlement,
attribution, reputation) already exists on Solana/Base; the one thing a chain cannot do is prove
that a model actually ran the job you paid for. So the chain settles and attributes, and a
verifier does the proving. What this experiment builds: the job → receipt → batched settlement
loop, measured on real hardware.

## Measured (2026-11-10)

`python3 mina.py` — the same "text a quote for an inbound HVAC lead" job, run on **this box**
(Ryzen 5 5625U, 12 threads, no discrete GPU, `qwen2.5:3b` via ollama), energy read from the
RAPL counter around the run:

| | local miner (this mini PC) | wholesale API (e108) |
|---|---|---|
| wall | 3.7 s | ~1 s |
| output | 52 tokens @ 14.1 tok/s | 77 tokens |
| energy | **35 J** (CPU package) | — |
| cost per job | **$0.0000015** | $0.00006 |
| monthly cost, 304 jobs/business | $0.0005 | $0.018 |

So **compute is not the scarce thing** — a $400 mini PC already serves the workload of roughly
**2,300 businesses** (710k jobs/month at 3.7 s vs 304 jobs/month per two-truck shop). The scarce
things are trust, distribution and attention.

The quality gap is real and visible: the local 3B model wrote a plausible SMS but missed the
question that unlocks the exact price and got the visit window wrong; the API model nailed both.
Small-model parity is a per-vertical evaluation question, never an assumption.

**Settlement granularity kills per-job settlement.** Solana base fee measured today:
**5,000 lamports = $0.000431 per transaction** — **7.2× the entire API cost of one job**.
A network that settles job by job is negative before it does any work. Hence: batch, or only
settle flows whose unit is cents (a voice minute), never micro-cents.

## Design (what survives contact with these numbers)

1. **No new L1.** Solana (or Base) for settlement + attribution. A new consensus layer adds cost
   and governance without adding trust in the one thing that matters.
2. **Jobs, not blocks.** A job carries: spec, workflow id, price ceiling, client id, referral id.
   A miner answers, and returns a **receipt**: input hash, model+quantization, token counts,
   joules, price, nonce, and a signature. The receipt is the unit of proof, payment and reputation.
3. **Verification, three tiers by value**: deterministic decode (temperature 0, fixed seed) →
   output hash; random spot-check recompute by an independent verifier with slashing on mismatch;
   TEE attestation only for jobs big enough to pay for it. Never redundant execution for
   micro-cents — it costs more than the job.
4. **Rewards come from fees, never emissions.** A miner earns only what a client paid, minus the
   network fee. No inflation, no token that trades on volume: a token, if any, is a claim on
   attributed USD revenue (p4 rule).
5. **The miners are the customers.** A contractor's PC sits idle ~20 h/day; it serves quotes for
   other businesses in the network and earns back more than its own subscription costs. Hardware
   is already sunk, so the "small profit over cost" is genuinely small — which is exactly what
   makes it work. Each business is simultaneously buyer, supplier and distribution channel.

## MVP, in order (each step measurable)

1. `job` + `receipt` + `worker` on this machine, batched settlement on **Solana devnet** in USDC:
   measure real $/job, latency, and receipt verification rate.
2. Two real businesses as miners (the owner's own machines first), one vertical (HVAC quotes).
3. Only then a token, and only as a claim on the fees the network actually collected.

## Files

| File | What |
|---|---|
| `mina.py` | measures one real job on local hardware: energy (RAPL), latency, tokens/s, $/job, against the API baseline. Writes `data/mina.json`. |
| `config.json` | machine values (ollama URL, model, energy counter, $/kWh) + the API baseline + settlement choice. Nothing hardcoded. |

## Rules

- Standing rules apply. No token, no chain, no emission before step 1 has real receipts and real
  fees behind it.
- Energy measured here is the CPU package only; a whole-machine figure must be measured before
  quoting miner margins to anyone.
- Never promise a miner a profit in SOL terms: payout rates are set at payout time, price is USD
  (same rule as the credits decision).
