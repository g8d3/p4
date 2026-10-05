# Trends SUMMARY — raw material for user verification (2026-10-05)

Scope: 7 topics × 2–3 signals, all from live tinyfish search/fetch today.
No app code written, no DECISION.md. Note: `evidence/VERDICT.md` (Phase 1)
does not exist yet — every signal below was verified live by this scout run.
Legend: VERIFIED = page fetched, exact quote saved. THIN = search snippet
only, needs a fetch before any locked claim.

## Top 5 candidate app angles emerging from the signals

### A1 — OSS-backed token launchpad on Solana (user's core idea — supported)
- Signal: Pump.fun proved the rails (11.9M+ tokens, $800M+ revenue, $1.3B ICO,
  1% bonding-curve fee, 0.05% creator share) AND the failure mode (98.6% of
  tokens showed rug-pull behavior, only ~1.4% graduate).
  VERIFIED — trends/launchpads.md S1 (Phemex, 2026-02-17)
- Signal: creator-fee competition is the live battleground (Bonk.fun 0.1% vs
  Pump.fun 0.05%; new entrants like StonkFun stealing single days).
  VERIFIED (Smithii) + THIN (StonkFun snippet) — trends/launchpads.md S2/S3
- Signal: TEA Protocol already stakes tokens on OSS projects with revenue
  sharing ("Share in project returns", teaRank, mainnet on Base preparing).
  Nobody found doing this on Solana + AI-agent-monetized projects.
  VERIFIED — trends/oss-monetization.md S1 (MEXC, 2026-09-21)
- Angle: the gap is real — "easy launchpad + OSS backing + contributor
  revenue share" has no verified Solana incumbent in this scout.

### A2 — Funding-arb yield feed as the token's "backing story"
- Signal: strategy guides with worked math are current (2026-04-28 guide:
  8–18% annualized normal, 55–110% in bullish windows, $2–3k minimum capital).
  VERIFIED — trends/funding-arb.md S1
- Signal: the 2026+ outlook says edge moved to automation + cross-venue
  (CEX vs on-chain perps on Hyperliquid/Drift) scanning — a scanner product,
  not a manual guide. VERIFIED — trends/funding-arb.md S2
- Angle: an OSS-token launchpad whose backing projects include (or are) an
  open-source funding-arb scanner fits two user topics at once. Thin part: no
  signal that retail wants "arb-backed tokens" — that framing is ours, not
  the market's.

### A3 — Prediction-market / skill-game monetization rail
- Signal: $45.33B combined volume Aug 2026 (from <$5B Sep 2025), Kalshi ~82%,
  both founders above $20B valuation; perps launched on both (Polymarket
  perps live Sep 3, Kalshi BTC perps >$1B in a week); POLY token + airdrop
  expected late 2026. VERIFIED — trends/gambling-skill-games.md S1
- Signal: crypto-native entrants blend sportsbook+casino+prediction in one
  account (Dexsport, Sep 2026, 1–2% built-in spread).
  VERIFIED — trends/gambling-skill-games.md S2
- Angle: skill-game or prediction contests as the engagement/monetization
  layer around token launches (e.g. trading competitions on graduated tokens).
  Honest caveat: NO signal found for pure skill-games (chess/poker-style
  crypto) this round — only prediction markets. Needs a second sweep or user pointer.

### A4 — AI-agent micropayment monetization for OSS projects
- Signal: Cloudflare Monetization Gateway (Jul 2026) lets any site charge AI
  agents per request in stablecoins via x402 (built with Coinbase +20 firms);
  x402 did ~$18M organic volume since May 2025; Cloudflare fronts ~20% of the web.
  VERIFIED — trends/ai-agents.md S2
- Signal: agent-token layer exists (Virtuals $365–410M mcap, Solana's
  Griffain, Kite payments-L1 mainnet Apr 2026) but flagged as thin-liquidity
  speculation. VERIFIED — trends/ai-agents.md S1
- Angle: OSS projects monetized via agent-payable APIs (per-call stablecoin
  revenue flowing back to contributors) is the concrete mechanism behind the
  user's "OSS monetized via AI agents" — Cloudflare/x402 is the rail to build on.

### A5 — Solana as the deployment chain (structural, not cyclical)
- Signal: 9 straight quarters leading all chains in dApp revenue ($257M Q2
  2026; Pump.fun 42% + Axiom 20% of Q1); record 14.2B tx in Q3 2026 (+45%
  QoQ), 8.38M SOL wallets, $262.7M on-chain card volume.
  VERIFIED — trends/solana.md S1/S2
- Counter-signal (keep honest): revenue concentrates in memecoin infra; web3
  gaming tokens sit -97% to -99.8% with >90% of games failed (Caladan via
  CryptoTicker, Sep 2026). A launchpad play inherits that cyclicality.
  VERIFIED — trends/videogames.md S1

## Confidence map
- VERIFIED (fetched, quoted): Solana revenue/tx; Pump.fun scale+fees;
  Pump-vs-Bonk fees; funding-arb guide + outlook; gaming post-mortem +
  MapleStory/OTG exceptions; prediction $45B + fees; agent tokens + x402;
  TEA + Gitcoin models.
- THIN (snippet only, re-verify before DECISION.md): Solana $3.06B DEX day;
  StonkFun $1.5M day; Solana Sept game list; Star Atlas L1 Dec; CZ "1M×
  payments" quote; TEA airdrop lineup.
- MISSING: pure skill-game signals; Drips/OpenCollective/GitHub Sponsors
  current numbers; any Solana OSS-token incumbent.

## Open questions for the user
1. A1 framing: token backed by 1+ OSS projects — should backing mean
   (a) revenue share from agent-API income, (b) TEA-style staking, or (c) both?
2. A2: is funding-arb a launch feature (scanner inside the app) or just the
   treasury strategy for backing? These are very different builds.
3. A3: prediction contests around launches — in scope for the prototype, or
   cut to keep Phase 3 minimal?
4. A4: x402 agent-payments as the OSS monetization rail — adopt as assumption,
   or do you know a different rail you prefer?
5. THIN items above: re-verify now (second sweep), or drop them and lock only
   VERIFIED signals?
6. Trends confirmed ("eso está correcto")? On your go-ahead, Phase 3 starts
   with DECISION.md — not before.
