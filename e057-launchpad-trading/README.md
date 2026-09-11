# e057 — launchpad trading: strategies, LP planning, and the product around them

Origin: 2026-09-10, from a question about positioning for the Arc mainnet launch (2026-09-16) that
turned into a general problem — *how do you trade and LP the tens of thousands of tokens that
permissionless launchpads emit, on any chain?*

## What is here

| File | Content |
|---|---|
| [`STRATEGY.md`](STRATEGY.md) | The trading + LP system: base rates, levels, entry/exit/kill rules, portfolio sizing, the LP rung algorithm, volume-profile construction, the measurement backlog. **Start here.** |
| [`APP.md`](APP.md) | The web app: gap analysis, MVP scope, data stack with verified limits/prices, monetization, social-volume feasibility (TinyFish vs X API), risks. |
| [`research/base-rates-and-data.md`](research/base-rates-and-data.md) | Survival/graduation base rates with sources, filters with documented predictive value, API feasibility table (incl. Arc 5042), X/social feasibility (tested). |
| [`research/lp-strategies-and-math.md`](research/lp-strategies-and-math.md) | Bid-side CLMM mechanics with derivations, worked examples, failure modes, evidence from the field, tooling/SDKs, venue feasibility by chain. |
| [`research/product-and-monetization.md`](research/product-and-monetization.md) | Competitor pricing table, revenue mechanics with real numbers, token-model precedents and outcomes, distribution playbook, gap analysis. |
| [`research/bid-ladder-math.py`](research/bid-ladder-math.py) | Standalone script reproducing the ladder tables in STRATEGY.md. `python3 research/bid-ladder-math.py` |

## The three findings that changed the plan

1. **A bid-side LP range (-50% to -95% below ATH) has its upside capped at exactly par.** It is a
   limit-buy ladder with a geometric-mean entry (`√(pa·pb)`, i.e. -84.2% for that range) and a
   short-put payoff: fees are the premium, the token's trip to zero is the notional. A bounce back to
   the top of the range returns your capital and zero tokens. To monetize a bounce you must withdraw
   near the trough and switch to spot or an ask-side range.
2. **Fees cannot pay for a completed fill** (~68 full traversals per fill needed at a 1% fee tier),
   and capital density is *highest* at the bottom of the ladder, not at the top — the opposite of the
   usual intuition.
3. **The rebound base rate is undocumented.** 68.7% of pump.fun tokens die on launch day, 4.55%
   survive 90 days, graduation is 0.2-1.4% by regime, and *no* public dataset answers "after -90%,
   what fraction recovers how much". That missing table is both the reason to measure before trading
   and the product's only durable moat.

## Next steps (in order)

1. **G1 — build the rebound base-rate table** for one chain (Solana/Meteora), including dead tokens,
   de-washed volume, per drawdown bucket. This is the input every strategy decision needs.
2. **G3 — backtest the bid-side ladder** (time-in-range, fee capture net of other LPs/JIT, inventory
   at exit vs a hold-quote benchmark) using the same dataset.
3. **G2 — measure intra-cohort correlation** to decide whether 15 concurrent positions is
   diversification or leverage.
4. Then paper-trade `STRATEGY.md` §2.2 and only then size real capital.

Arc-specific: nothing on-chain before the 2026-09-16 mainnet; the near-term Arc play is the data gap
(no aggregator indexes chain 5042), not the launchpad tokens.

Conventions: see [`AGENTS.md`](AGENTS.md).
