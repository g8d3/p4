# Revenue split v2 — own-token trading vs product revenue (2026-10-25)

Read-only research. **No trading, wallets or keys.** Supersedes `coco/revenue_split_2026-10-25.md`: v1 wrongly treated all trading fees as "casino" activity. Nova's definition is **trading of the project's own coin**, so a DEX/perp/launchpad earning fees from other people's pairs is product revenue. This version adds a product type, estimates the own-token share where cheap, and applies one rule to every token.

Data fetched 2026-10-25 ~18:53 Bogotá (UTC-5):
- 30d fees/revenue: `https://api.llama.fi/summary/fees/<slug>?dataType=dailyFees|dailyRevenue`
- 24h protocol volume: `https://api.llama.fi/summary/dexs/<slug>?dataType=dailyVolume` (aggregators: `/summary/aggregators/jupiter-aggregator`)
- 24h own-token pool volume: `https://api.geckoterminal.com/api/v2/networks/<network>/tokens/<address>/pools?page=1` (top 20 pools by h24)
- Hyperliquid own-token volume: `POST https://api.hyperliquid.xyz/info` `{"type":"metaAndAssetCtxs"}`

## Rule (one rule for all)

- **own-token trading share** = volume of pools/pairs containing the project token on its own venue ÷ that venue's total volume. It is a **volume proxy for revenue share** (fee tiers vary), 24 h, top-20 pools; "≈" means estimate.
- Labels: **real business** <25% own-token; **hybrid** 25–75%; **casino coin** >75%; **unknown** where no honest estimate exists.
- Chains: protocol fees are gas for blockspace, not fees on trading the chain's coin → own-token trading **0%** by definition. Gas still depends on on-chain trading activity; noted separately. Same rule → ETH, BNB, SOL, NEAR all real business (no more arbitrary split).
- Product type is separate from the label. A launchpad trading other memecoins is product revenue even if the activity is speculative.

## Summary (30d fees/revenue; own-token share 24h proxy)

| Token | Product type | Own-token share | Label | 30d fees | 30d revenue | Speculative-activity note |
|---|---|---:|---|---:|---:|---|
| ETH | chain | 0% (gas, not ETH trading fees) | **real business** | $15,778,188 | $5,390,745 | gas demand is cyclical; revenue is burn, not company income |
| BNB | chain | 0% (BSC gas) | **real business** | $14,279,574 | $1,427,954 | Binance CEX revenue not in DefiLlama; BSC gas only |
| SOL | chain | 0% (gas) | **real business** | $25,937,465 | $3,174,943 | priority fees track on-chain trading activity |
| NEAR | chain | 0% (gas) | **real business** | $219,255 | $153,475 | tiny fee base |
| TAO | unknown | unknown | **unknown** | — | — | no DefiLlama fees entry |
| LINK | oracle | 0% (service fees, not LINK trading) | **real business** | $156,461 | $0 | all fees go to node operators |
| HYPE | perps (+ spot) | **≈7.15%** (HYPE perp volume / all perps) | **real business** | $80,360,632 | $64,396,630 | perp revenue depends on speculative volume; spot HYPE share unknown |
| JUP | DEX aggregator + perps + DCA | **≈0.40%** (rough) | **real business** | $11,122,849 | $3,984,794 | aggregator/perps revenue depends on trading volume |
| RAY | DEX | **≈3.16%** | **real business** | $14,229,432 | $2,203,436 | swap volume is speculative |
| ORCA | DEX | **≈0.39%** | **real business** | $7,762,435 | $1,009,117 | swap volume is speculative |
| PUMP | launchpad + DEX | **≈2.07%** (PUMP pools / launchpad+swap volume) | **real business** | $179,493,702 | $62,021,587 | launchpad activity is memecoin speculation; PUMP itself is ~1–4% |
| UNI | DEX | **≈0.21%** | **real business** | $93,372,855 | $7,602,870 | swap volume is speculative |
| CAKE | DEX + prediction/lottery | **≈0.21%** | **real business** | $12,464,711 | $4,156,117 | AMM + gambling volume are speculative |
| AERO | DEX | **≈2.22%** | **real business** | $10,374,019 | $6,968,321 | swap volume is speculative; bribes in v1 fees, not separable |

**Result: none of the 14 is a casino coin under Nova's own-token definition.** TAO is unknown. The "speculative-activity" column is the honest risk note v1 was trying to express.

## Own-token estimates (how each was built)

| Token | Own-token volume (24h, source) | Venue total (24h) | Share | Caveat |
|---|---|---:|---:|---|
| RAY | $3,030,209 — RAY pools on Raydium (`raydium-clmm` $2,200,533 + `raydium` $829,676) | $95,846,832 (Raydium AMM) | 3.16% | one chain; top pools |
| ORCA | $484,499 — ORCA pools on Orca | $123,009,380 (Orca) | 0.39% | top 20 only |
| JUP | $1,518,548 — JUP pools across Solana DEXs (top 20) | $376,677,055 (Jupiter Aggregator) | 0.40% | **rough**: JUP pools are not the same as Jupiter-routed volume |
| UNI | $2,601,904 — UNI pools on Uniswap Ethereum (`v3` $1,556,832 + `v4` $966,492 + `v2` $78,580) | $1,245,596,365 (Uniswap global 24h) | 0.21% | Ethereum pools only; global denominator understates slightly |
| CAKE | $1,756,490 — CAKE pools on PancakeSwap BSC | $821,088,708 (PancakeSwap global) | 0.21% | BSC pools only |
| AERO | $2,793,679 — AERO pools on Aerodrome Base (`slipstream` $1,844,979 + `v1` $572,731 + other slipstreams) | $125,767,617 (Aerodrome) | 2.22% | top pools; v1 includes bribes in fees, not volume |
| PUMP | $4,807,721 — PUMP pools on PumpSwap | $231,854,419 (PumpSwap $112.7M + pump.fun launchpad $119.1M) | 2.07% | launchpad fees trade other tokens; own-token revenue share ≈1.1% |
| HYPE | $209,333,859 HYPE perp volume | $2,927,552,048 all Hyperliquid perps | 7.15% | spot HYPE pair not found in the spot context; perps proxy |

Chains: own-token trading share is **0% by construction** (the fee is gas for blockspace, not a fee on trading ETH/BNB/SOL/NEAR). On-chain trading volume still drives gas; that is the speculative-activity note, not a casino label.

LINK: oracle fees (Requests/Keepers/VRF/CCIP) are paid for data services; 0% is from trading LINK itself. `chainlink-staking` is a separate token/staking mechanism and is excluded.

## Unknowns kept unknown

- **TAO**: no DefiLlama fees entry (`summary/fees/bittensor` and `/tao` return 400); no estimate.
- **HYPE spot**: HYPE/USDC did not appear in the spot asset contexts used; only the perp proxy is given.
- **JUP**: own-token pool volume across DEXs is not Jupiter's routed volume; 0.40% is explicitly rough.
- **AERO**: bribe component of V1 fees is not separable from swap fees.
- **Chains**: no split of gas by transaction type; own-token trading fees are zero, but trading-driven gas is not separated.
- **BNB**: Binance exchange revenue is outside DefiLlama.
- **LINK**: `chainlink-requests` revenue is $0 (all to node operators); staking revenue separate.

## Sources per coin (fees/revenue + own-token volume)

- **ETH** — fees/revenue `.../fees/ethereum`; product = chain gas.
- **BNB** — `.../fees/bsc`; product = BSC gas.
- **SOL** — `.../fees/solana`; product = chain gas.
- **NEAR** — `.../fees/near`; product = chain gas.
- **TAO** — no fee entry.
- **LINK** — `.../fees/chainlink-requests` (staking: `.../fees/chainlink-staking`, excluded).
- **HYPE** — `.../fees/hyperliquid-perps`, `.../fees/hyperliquid-spot-orderbook`; volume `POST api.hyperliquid.xyz/info {"type":"metaAndAssetCtxs"}`.
- **JUP** — `.../fees/jupiter-aggregator`, `/jupiter-perpetual-exchange`, `/jupiter-dca`, `/jupiter-studio`, `/jupiter-staked-sol`; volume `.../summary/aggregators/jupiter-aggregator`; pool volume `https://api.geckoterminal.com/api/v2/networks/solana/tokens/JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN/pools`.
- **RAY** — `.../fees/raydium-amm`, `.../summary/dexs/raydium-amm`; pools `.../networks/solana/tokens/4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R/pools`.
- **ORCA** — `.../fees/orca-dex`, `.../summary/dexs/orca-dex`; pools `.../networks/solana/tokens/orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE/pools`.
- **PUMP** — `.../fees/pump.fun`, `.../fees/pumpswap`; volumes `.../summary/dexs/pump.fun`, `/pumpswap`; pools `.../networks/solana/tokens/pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn/pools`.
- **UNI** — `.../fees/uniswap-v2|v3|v4`, `.../summary/dexs/uniswap-v2|v3|v4`; pools `.../networks/eth/tokens/0x1f9840a85d5af5bf1d1762f925bdaddc4201f984/pools`.
- **CAKE** — `.../fees/pancakeswap-amm|amm-v3|stableswap|infinity|prediction|lottery`; volumes `.../summary/dexs/pancakeswap-amm|amm-v3|stableswap|infinity`; pools `.../networks/bsc/tokens/0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82/pools`.
- **AERO** — `.../fees/aerodrome-v1|slipstream`, `.../summary/dexs/aerodrome-v1|slipstream`; pools `.../networks/base/tokens/0x940181a94a35a4569e4529a3cdfb74e38fd98631/pools`.

API base for the short paths above: `https://api.llama.fi`. GeckoTerminal base: `https://api.geckoterminal.com/api/v2` (top 20 pools, `volume_usd.h24`; 24h snapshot, not 30d). Fees/revenue are rolling 30d from the same fetch as v1.
