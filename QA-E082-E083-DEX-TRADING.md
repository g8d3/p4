# Q&A — ideas like the forever-harness and ScrapeNet, trading connections, bear-market businesses

Date: 2026-09-29. Context: e082-forever-harness (agent loop that works indefinitely
without quality collapse, shipped as plugin) and e083-scrapenet (browser extension
that intercepts requests, transforms and saves them, publishes data as API,
monetizes via a scraping network with crypto payouts and AI-improved transforms).

---

## Q1: What ideas occur to you similar to the ones I proposed?

1. **Ever-bounty board** — agents post bounties to each other, escrow in crypto,
   settlement on proof (tests PASS + review). e082 keeps workers running forever;
   bounties give them something to do. Survives bear markets because work, not
   speculation, is the product.
2. **Private-data union** — like ScrapeNet but for data users already own:
   exchange order history, fill logs, Telegram alpha groups, screenshots.
   Extension redacts + normalizes locally; only aggregates leave the machine.
   Members get paid when their data improves a shared model.
3. **Skill foundry** — every time an agent solves something once, it mints a
   reusable skill/recipe (like ScrapeNet recipes but for agent work:
   "fetch funding rates", "backtest a perp strategy"). Skills get versioned,
   rated, and rented. The missing compounding layer for e082.
4. **Agent audit trail** — append-only, signed log of what every long-running
   agent did, what it spent, what it produced. Required the moment agents
   handle money. Natural sidecar to e082.

## Q2: What improvements to these two ideas occur to you?

**e082 (forever harness):**
- Adversarial reviewer: a second cheap pass that tries to reject each cycle's
  work. Single biggest quality lever for infinite loops.
- Spend-to-earn accounting: each cycle logs cost vs value produced; the loop
  throttles itself when ROI goes negative. The bear-market survival switch.
- Skill extraction on finish: every N cycles, distill what worked into
  `skills/` so future cycles get cheaper.

**e083 (ScrapeNet):**
- Move transform into the extension (local recipe execution) so raw pages never
  leave the device — only normalized records ship. Makes the privacy story
  sellable.
- Schema registry + price per schema: rare, fresh, hard-to-scrape datasets pay
  more; commodity data pays ~zero. Commission logic exists, needs tiering.
- Dataset backtesting hook: buyers run a strategy against the dataset before
  subscribing. Turns data from a gamble into a trial.

## Q3: What use cases do you see for these applications?

- e082: overnight repo janitor, docs that never rot, competitor-price watcher
  filing weekly reports, strategy-lab runner backtesting one variant per cycle
  forever.
- e083: distributed price/funding/liquidity capture from geo-blocked venues,
  job-listing and product-price feeds, Telegram/Discord alpha scraping with
  revenue share to posters, niche B2B datasets (e.g. LATAM exchange prices) no
  centralized vendor covers.

## Q4: What connections do you see with apps that help trading as maker or taker on DEXs (AMM or CLOB)?

1. **ScrapeNet as a trading-data network.** DEX data is fragmented: quotes,
   depths, funding, borrow rates, and CLOB order-book snapshots differ per
   region/endpoint and get geo-limited or rate-limited. A fleet of
   extension/node operators each streaming order-book top-of-book + spread +
   depth + funding is exactly a decentralized market-data feed. Consumers:
   market makers needing multi-venue spread data.
2. **Maker side:** e082 running forever as a quoting-parameter tuner — one
   cycle per day re-fits spread/inventory-skew from the ScrapeNet feed; verify
   gate = simulated fill PnL must beat baseline before new params go live.
   Quality gates prevent the classic "loop degrades the quoting model" failure.
3. **Taker side:** latency/fee arb needs fresh, unusual data (which venue lags,
   where size sits). ScrapeNet nodes near different venues detect the lag; the
   e082 loop evaluates taker routes and kills them the cycle they decay. Taker
   edges die fast — an infinite loop with a kill-gate is the right shape.
4. **AMM vs CLOB bridge:** AMM (pool price, fee tier, tick liquidity) + CLOB
   (bids/asks, spread, imbalance) in one normalized schema is genuinely useful
   and nobody gives it away free. ScrapeNet recipes are that normalizer;
   publish it as one API.

## Q5: What connections do you see with ideas for trading strategies or profitable businesses that survive bear markets?

Bear markets kill speculation but not costs and compliance. Sell shovels:

- **Data subscriptions with usage proof** (ScrapeNet publish + earnings ledger
  already meters usage). Price in stables, pay node operators in stables; keep
  crypto rails, remove volatility.
- **Audit/compliance feeds:** proof-of-price, proof-of-liquidity snapshots for
  funds and market makers. Regulators and LPs pay in downturns.
- **Cost-cutting automation** (e082 as a service): reconciliation, reporting,
  risk checks — sold as "one loop, one report, flat monthly fee."
- **Strategy graveyard + marketplace:** every dead strategy becomes a
  dataset/skill others rent. In a bear market the catalog of what *doesn't*
  work is itself worth money.

Concrete next build: **e084-mm-data-loop** — ScrapeNet recipe for 2–3 DEX
venues (book snapshot + funding) feeding an e082 loop that paper-trades maker
params daily, publishes fills as a ScrapeNet dataset, with paper-PnL per
contributor on the earnings board. One experiment proving the whole trading
connection.
