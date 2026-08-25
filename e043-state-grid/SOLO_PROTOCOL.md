# e043 — SOLO_PROTOCOL: how to keep working alone (and actually find value)

For the beginner working solo, trying to find something valuable. The method
that makes solo work viable — everything in here is already proven by this
experiment's own history (see FASE1/FASE2_FINDINGS.md).

## What "something valuable" can mean (pick your level)

| Level | Realistic? | How long |
|---|---|---|
| **1. A documented, honest process** — you can validate ANY strategy and explain why it wins/loses | ✅ Yes | Weeks of practice |
| **2. A validated thin edge** — PF 1.05–1.15, after fees, out-of-sample-checked, with strict risk rules | ✅ Yes, rare and fragile | Months |
| **3. A money-printer backtest** (+50% without caveats) | ❌ Almost always an error | — |

Funds pay people to do Level 1. The course you are building is Level 1 made
concrete. **Level 1 + honest Level 2 over years is a real career. Level 3 is a
fantasy you should hunt to DISPROVE, not to confirm.**

## The loop (one page)

```
1. Write the hypothesis IN WORDS before any code:
   "If X happens, the next move is likely Y, because Z."
2. Build the smallest test that can FAIL it (A/B on/off, same data).
3. Run it. Record the numbers. Record WHAT WOULD HAVE CONVINCED YOU BEFOREHAND.
4. Keep it ONLY if it survives out-of-sample (60/40 split).
5. One bucket: "kept". One bucket: "rejected with reason".
   Go back to 1.
```

## The 7 rules (each backed by this experiment's evidence)

1. **One change at a time.** Ever. Three-tier discipline: structural defaults,
   ladder shapes rarely, adaptive mappings one at a time.
2. **Out-of-sample or it doesn't count.** We caught our own fake edge (+0.93%
   that was a cold-EMA bug) only by re-checking. If you don't split train/test,
   you are fitting noise. Every single claim needs an OOS check.
3. **Fees first, always.** A strategy that wins before fees and loses after is
   not a strategy — it's a donation. Our 5m ladder: $15k fees on $100k.
4. **The entry quality is the bottleneck, not the knobs.** Two sweeps (216
   configs each) stayed negative because the ENTRY won ~40% when ~67% was
   needed. More parameters fix nothing; better hypotheses fix things.
5. **Bound every search with a stopping rule.** Ours: stop at "edge found" OR
   "budget exhausted" — whichever first. A search without a budget is a
   treadmill. Write the budget BEFORE starting.
6. **Keep a reject log.** Every failed idea, with why. It is your real
   intellectual capital — most traders never build one, and it is why you'll
   get better and they won't.
7. **When a result surprises you, suspect the code.** The accident that looked
   like +0.93% was a bug; the −858% was real. Verify accounting by hand on a
   single trade before trusting any claim.

## The one weakness of solo work — and its fix

The killer is not lack of ideas. It's **self-deception**: when you're alone,
every bias has an empty chair. The fix is not a mentor — it's a **falsifier**:
someone or something whose only job is to try to break your claim.

Practical versions: (a) publish your results somewhere and invite questions,
(b) find ONE person who will argue with you, (c) every few experiments, hand a
claim to an agent/assistant with the explicit task "try to break this". That
single habit converts solo work from risky to viable.

## Templates

**Candidate card** (write BEFORE any compute; the prior comes from
BASE_RATES.md, the screens from `bin/screen.py`):
```
ID: ___                      (one idea = one card = one A/B)
HYPOTHESIS: ___
SIGNAL (what I measure): ___
MECHANISM (why it might work): ___
WHO PAYS? (what counterpart, what asymmetry): ___   ← empty = reject on sight
DATA SOURCE + TIMEFRAME: ___                        (see Data-source card)
PRIOR (from BASE_RATES + screens A/B/C): ___        (cheap screens, no engine)
INTERESTING ONLY IF: ___                            (page: WR > breakeven_B etc)
WOULD CONVINCE ME IF: ___      ← write BEFORE running
RESULT (after fees): ___
OOS CHECK (60/40): ___
VERDICT: keep / reject — because ___
```

**Data-source card** — the data layer is picked by the SAME discipline, so the
"good data needs good intuition" recursion breaks:
```
VARIABLE + what human-opinion fact it measures: ___
CRYPTO ANALOG of equity ratio (if any): ___    (P/E→miner rev, P/B→MVRV, P/S→fee rev, PEG→fee growth, comps→BTC vs ETH/gold/NDX)
SCALE it can influence: ___    (5m entry / 1h allocation / weekly regime) — never mix
AVAILABILITY + cost: ___
FALSIFIER (cheapest test, e.g. "funding z>1 predicts 30d OOS?"): ___
STATUS: candidate / screened / rejected (— why)
```
Rule that kills the recursion: a data source earns its place only after its
falsifier passes — you do NOT need intuition to choose data; you need a cheap
test. Intuition is only needed to *name candidates*; the screens vet them.

**Reject log** (append-only)
```
DATE | IDEA | WHY IT FAILED | WHAT IT TAUGHT
```

## Recommended solo path

1. Become the **validator** first: pick a documented, published edge, reproduce
   it, then try to break it. That trains the muscle that matters.
2. Then test ONE data-driven hypothesis at a time (book walls, funding,
   volatility) as Tier-3 mappings — never unfiltered sweeps.
3. Keep the course as the compounding asset: every finding, in plain language,
   becomes a lesson. Teaching is itself an edge: it forces honesty, and it has
   a market.