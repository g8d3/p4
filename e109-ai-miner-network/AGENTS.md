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

## The loop, measured with no chain at all (2026-11-10)

`python3 flujo.py 9` runs the whole thing: buyer posts 9 jobs (3 workflows), a signed worker
answers, receipts are verified, one in three is spot-checked by re-execution, commissions are
own first-touch, and the batch closes on a merkle root.

| measured | value |
|---|---|
| signature verification | **9/9** |
| spot-check re-execution | **3/3 exact** (same spec, same seed → same hash) |
| latency mean | 8.5 s/job |
| energy mean | 129.6 J/job → **$0.0000054** at $0.15/kWh |
| sale price used | $0.00006/job (the API baseline) |
| ledger | 6 unique jobs (identical spec = identical job id: idempotent by construction) |
| commission owed | $0.000081 to 2 referrers, 15% first-touch |
| network fee | $0.000036 |
| chain used | **none** — the merkle root is the anchor |

That is the crux: **re-execution reproduces the output exactly**, so a verifier can catch a lying
miner without a chain, without redundancy on every job, and without trusting us. One in three
spot-checks already makes cheating unprofitable at this price level.

## Is a blockchain needed? (the honest answer)

Not for compute, not for inference, not for KYC. This loop proves the first two: the loop is a job
queue, ed25519 receipts and a SQLite ledger, and the chain adds nothing to the work.

The chain earns its place only where someone **other than us** must verify or be paid:

1. **Independent audit** — a miner proving its own payouts, a referrer proving its commission, a
   client proving a receipt root, without trusting our database. Until a third party asks, a
   database row is enough.
2. **Paying contributors who have no bank** — USDC payouts to people worldwide are the real
   advantage of crypto rails, and a chain (Solana) is the cheapest way to do that without opening
   accounts in every country.
3. **Transferable claims on revenue** — a token, if it ever exists, needs a chain to be transferable.

What a chain does **not** do here: prove that a model ran, hold a business's identity, or satisfy
KYC. KYC is an off-chain, licensed, human process (documents, sanctions screening, recordkeeping,
liability). A chain can only *record* the result of a KYC check — never perform it. So a business
that needs compliance needs an accountable entity (us, or a licensed partner), and the network's
"compliance-as-a-service" idea is a licensing business, not a chain feature.

**Cost of the anchor**: $0.00043 per batch transaction (base fee, measured) — 1/9 of a 9-job
batch, 1/900 of a 100-job batch, and 7× the price of one job. Per-job settlement stays forbidden.

`anclar.py` is the plug, complete and tested up to the point of funding: the devnet faucet
rate-limited this machine (2 attempts, 2026-11-10), so the batch is anchored by its root in
`batches.root` and `batches.anchor` stays NULL until `keys/devnet.json` is funded.

## Dynamic costs — after the owner caught a constant (2026-11-10)

The first version priced a job from one number copied off a vendor page. It was **5.7x too
expensive**: the live feed prices `z-ai/glm-5.3-flash:batch` at **$0.033/M in, $0.061/M out**,
while the coding-plan page lists $0.15 / $0.50 for its non-batch sibling.

Cost is now a function, never a constant: `python3 precios.py`

- feed: OpenRouter's public catalogue (441 models, per-token prices, no key), cached 1h in
  `data/precios.json` with `_fetched_at`;
- tokens: measured on every receipt the network already stores;
- quote: `tokens x live price x tier multiple`, so any client or miner can recompute it.

**Two axes, deliberately separate.** Model choice is a quality decision (the cheapest one that
passes the workflow's floor, read from the feed); the tier is an ownership decision. Mixing them
produced a first attempt where the "plus" tier cost 40x the "owner" tier — a ladder nobody could
read. Measured today, per job:

| workflow | market cost | cost tier (1.1x) | co-build (3x, 15%) | owner (10x, 40%) |
|---|---|---|---|---|
| quote-by-text | $0.0000105 | $0.0000116 | $0.0000316 | $0.0001054 |
| estimate-to-paid | $0.0000253 | $0.0000279 | $0.0000760 | $0.0002532 |
| revenue-report | $0.0000249 | $0.0000274 | $0.0000748 | $0.0002494 |

Miner P&L on this box (energy $0.0000058/job): at the **cost** tier it keeps $0.000005/job, at
**owner** $0.000089/job. The loop in `flujo.py` now quotes every job from the feed — measured run:
6/6 signatures, 2/2 exact spot-checks, mean price $0.0000223/job, mean energy $0.0000059.

Still unpriced from a source (honest gaps): `usd_per_kwh` is an assumption ($0.15) until a real
bill or a smart plug says otherwise; `expected_tokens` are measured averages from receipts, so a
long job is under-quoted; and no workflow has a *quality evaluation* proving the cheapest model
passes its floor — that eval is the next thing to build.

## The scout → contract → registry loop

A scout agent does not sell software. It finds a business with a problem, talks to whoever owns it,
and puts a live-quoted number in front of them. What it closes is a **contract** (`contrato.py`):
scope, deliverable, tier, price, royalty share, signed by the client and the scout. The delivered
piece enters a **registry** as a component with named owners; every later reuse pays them.

```
python3 contrato.py close quote-by-text owner biz_dana agent_ref_3 scout_a
python3 contrato.py reuse comp_x biz_other 0.50
  -> sponsor (client) $0.20   builder (agent) $0.20   network $0.10
```

So the client is not renting a licence — it is buying a **position** in a piece of software that
other businesses will use. Three ways it pays back: the work itself (a human doing it costs ~1000x
more), the ownership share on reuse, and the referral commission if it brings the next business.

**Ledger**: `contracts` (signed), `components` (owners + share), `reuses` (fee split), plus the
receipts/batches from the work loop. Money is USD; crypto stays the rail.

**Legal, stated plainly**: this is a contractual, per-client, non-transferable revenue share. It
becomes a security the moment it is marketed as an investment, pooled, or made transferable —
so: no token on this mechanic without counsel. And the accountable entity for KYC, contracts and
tax is still a company (us or a licensed partner); the registry records ownership, it does not
create legal personhood.

## MVP, in order (each step measurable)

1. ✅ `job` → `receipt` → `worker` → verification → ledger → batch root (measured above).
2. Two real businesses as miners (the owner's own machines first), one vertical (HVAC quotes).
3. Solana settlement (USDC) + anchoring, once a third party actually needs to verify or be paid.
4. Only then a token, and only as a claim on the fees the network actually collected.

## Files

| File | What |
|---|---|
| `mina.py` | one real job on local hardware: energy (RAPL), latency, tokens/s, $/job, against the API baseline. Writes `data/mina.json`. |
| `recibo.py` | canonical job spec, ed25519 sign/verify, receipt (`job`, `out_sha`, tokens, joules, price), merkle root over a batch. Keys in `keys/` (0600, gitignored). |
| `libro.py` | SQLite ledger: agents, jobs, receipts, commissions (first-touch 15%), batches (root + anchor). USD everywhere; crypto is only the rail. |
| `worker.py` | the miner: `POST /job` → local model (temp 0, seed 42) → signed receipt + output; `GET /health`. |
| `flujo.py` | end-to-end measurement: 9 jobs, spot-checks by re-execution, ledger, batch root, `data/flujo.json`. |
| `energia.py` | RAPL joules around a call (root-only counter, sudo -n fallback). |
| `anclar.py` | writes the newest batch root on Solana devnet as a memo (one tx per batch), records `batches.anchor`. |
| `precios.py` | live cost feed (OpenRouter catalogue), `cost_usd(tokens, model)`, tier quotes, miner margin vs energy. Cached 1h. |
| `contrato.py` | quote / close / reuse: 3 ownership tiers, contract signed by client + scout, component registry, royalty split. |
| `config.json` | machine values (ollama URL, model, energy counter, $/kWh), expected tokens per workflow, pricing (feed URL, tiers, network fee), royalty split, settlement (devnet RPC + anchor cost). |

## Rules

- Standing rules apply. No token, no chain, no emission before step 1 has real receipts and real
  fees behind it.
- Energy measured here is the CPU package only; a whole-machine figure must be measured before
  quoting miner margins to anyone.
- Never promise a miner a profit in SOL terms: payout rates are set at payout time, price is USD
  (same rule as the credits decision).
