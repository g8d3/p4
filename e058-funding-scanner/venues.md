# Perp DEX venue table (decision tool for MVP cut)

Sources: (a) Loris 42-venue snapshot 2026-09-12 (market counts);
(b) DefiLlama `/protocols` 2026-09-12 (TVL; no volume field — capital
sits in **Bridge** entries, Perps TVL often 0, use Bridge as size proxy);
(c) live probes 2026-09-12 by this agent. e021 playground verified
FUNCTIONAL (boots 1s, 3 flows ok, scheduler running).

Legend: ✓ works, ~ partial, ? untested, ✗ blocked/expensive.

| Venue | Loris mkts | Size proxy (DefiLlama) | Public fund/depth/OI | Deposit rail | MVP |
|---|---|---|---|---|---|
| hyperliquid | 178 | Bridge $6.60B | ✓ / ✓ / ✓ | Arb USDC ~$0.30 | IN |
| aster | 560 | Bridge $537M | ✓ / ✓ / ✓ | Direct wallet Arb/BNB | IN |
| extended | 326 | Perps $117M | ✓ / ✓ / ~ | ? | IN |
| lighter | 217 | Bridge $618M / Perps $77M | ~ / ✗ / ✓ | ETH mainnet ✗ $$$ | MAYBE |
| paradex | 63 | Bridge $19M | ? / ✓ / ? | Interchain Arb/Base/Sol | IN |
| edgex | 164 | Bridge $67M | ? / ? / ? | ? | PROBE |
| variational | 553 | tvl 0 | ? / ? / ? | ? | PROBE |
| vest | 542 | n/a (name clash) | ? / ? / ? | ? | PROBE |
| grvt | 193 | Bridge $42M | ? / ? / ? | ? | PROBE |
| pacifica | 77 | Perps $25M (Solana) | ? / ? / ? | Solana? | PROBE |
| decibel | 73 | $29M (Aptos) | ? / ? / ? | ? | PROBE |
| risex | 31 | $17.8M (RISE) | ? / ? / ? | ? (values frozen?) | VERIFY |
| bluefin | 8 | Pro $1.7M (Sui) | ? / ? / ? | Sui (-80bps clamped?) | OUT |
| zo ("01") | 39 | n/a | ? / ? / ? | ? (JUP hi leg) | PROBE |
| txflow | 173 | n/a | ? / ? / ? | ? (JUP lo leg) | PROBE |
| nado/ondo/paragon/phoenix/qfex/reya/hibachi | 15–82 | n/a–small | ? | ? | PROBE |
| bullet/entropio/hotstuff/kinetiq/bullet | 4–35 | ~0 | ? | ? | OUT (thin) |

Not on Loris — phase-2 direct integrations: Jupiter Perps ($750M,
Solana), GMX V2 ($204M, Arb), Derive V2 ($155M, HL-L1+Ls), dYdX V4
($70M), Apex Omni ($31M), Aevo ($15.6M), Ostium ($14.6M, Arb),
Drift Trade ($0.64M, Solana), Gains ($10.3M), MUX ($9.3M).

## Is this table useful? Yes — it is the product decision

- **Maintenance is the cost**: each venue = an integration that breaks.
  Cut to 6–8 by: fundable rail + public APIs + real volume (DefiLlama).
- **DefiLlama answers "is it real"** (TVL/vol = usage, not listings).
- **Loris answers "does it price"** (market count per venue).
- **Probes answer "can we integrate"** (no-key depth/OI in minutes?).
- Stale-feed detection (KORU/DEEP) becomes the freshness feature.
