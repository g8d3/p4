# Revenue split — Nova portfolio tokens, DefiLlama fees vs revenue (2026-10-25)

Read-only research. **No trading, wallets, keys or orders.** Data fetched 2026-10-25 ~18:41 Bogotá (UTC-5) from the DefiLlama fees API:

- `https://api.llama.fi/summary/fees/<slug>?dataType=dailyFees`
- `https://api.llama.fi/summary/fees/<slug>?dataType=dailyRevenue`

`total30d` is the rolling 30-day figure; fees are what users pay, revenue is what the protocol/token captures (DefiLlama's own per-protocol methodology, quoted for each group below). USD, not annualized.

## Method and its honest limit

1. Each token is mapped to the DefiLlama protocol(s) that represent its on-chain business (table lists every slug). Chains use their chain-fee entry; BNB's Binance exchange revenue is **not** on DefiLlama.
2. "Trading-related" = fees from swaps, perps, bonding curves or launchpad trades, per the protocol methodology. "Own-token trading" = people buying/selling the project token itself. **DefiLlama does not expose pair-level or transaction-level breakdowns in this API**, so the own-token share is `unknown` for every coin. The table's share is the trading-related share of revenue (and of fees), not a claim about the own token.
3. Labels: **real business** = fees mostly from product use other than trading; **hybrid** = meaningful mix; **casino coin** = almost all fees from trading. Where the API cannot split the mix, the label carries `(split unknown)` instead of inventing one.
4. Revenue can be zero even with fees when the protocol passes everything to suppliers (Chainlink), and chain "revenue" is mostly burned gas, not company income. Both are flagged.

## Summary (30-day window)

| Token | Label | 30d fees | 30d revenue | Trading-related share of revenue / fees | Own-token trading | DefiLlama slugs |
|---|---|---:|---:|---|---|---|
| ETH | **real business** (blockspace; split unknown) | $15,778,188 | $5,390,745 | unknown / unknown — gas covers all on-chain use, not just trading | unknown | `ethereum` |
| BNB | **hybrid** (BSC gas only; CEX missing) | $14,279,574 | $1,427,954 | unknown / unknown — BSC gas is usage; Binance CEX revenue absent from DefiLlama | unknown | `bsc` |
| SOL | **hybrid** (gas/priority fees; split unknown) | $25,937,465 | $3,174,943 | unknown / unknown — all tx fees, no activity split | unknown | `solana` |
| NEAR | **real business** (gas; tiny) | $219,255 | $153,475 | unknown / unknown — all gas | unknown | `near` |
| TAO | **unknown** | — | — | unknown — no DefiLlama fees entry (404/400 on `bittensor`, `tao`) | unknown | none |
| LINK | **real business** | $156,461 | $0 | 0% / 0% — oracle requests/VRF/CCIP/Keepers fees; all fees go to node operators | 0% (no token-trading revenue) | `chainlink-requests` |
| HYPE | **casino coin** (trading-dominated; split unknown) | $80,360,632 | $64,396,630 | ≈all / ≈all — perps + spot fees; perps also include AQAv2 reserve yield, not separable | unknown | `hyperliquid-perps`, `hyperliquid-spot-orderbook` |
| JUP | **casino coin** (97% trading; LST/DCA remainder) | $11,122,849 | $3,984,794 | **97.1% / 80.3%** | unknown | `jupiter-aggregator`, `jupiter-perpetual-exchange`, `jupiter-dca`, `jupiter-studio`, `jupiter-staked-sol` |
| RAY | **casino coin** | $14,229,432 | $2,203,436 | **100% / 100%** | unknown | `raydium-amm` |
| ORCA | **casino coin** | $7,762,435 | $1,009,117 | **100% / 100%** | unknown | `orca-dex` |
| PUMP | **casino coin** | $179,493,702 | $62,021,587 | **100% / 100%** | unknown | `pump.fun`, `pumpswap` |
| UNI | **casino coin** | $93,372,855 | $7,602,870 | **100% / 100%** | unknown | `uniswap-v2`, `uniswap-v3`, `uniswap-v4` |
| CAKE | **casino coin** (trading + gambling) | $12,464,711 | $4,156,117 | **93.2% / 97.7%**; the rest is prediction/lottery, not trading | unknown | `pancakeswap-amm`, `pancakeswap-amm-v3`, `pancakeswap-stableswap`, `pancakeswap-infinity`, `pancakeswap-prediction`, `pancakeswap-lottery` |
| AERO | **casino coin** (DEX; bribe share unknown) | $10,374,019 | $6,968,321 | unknown / unknown — swap fees plus bribes (v1 methodology), bribes not separable | unknown | `aerodrome-v1`, `aerodrome-slipstream` |

## How each share was computed

- **JUP**: trading revenue = aggregator $2,080,986 + perps $1,687,207 + DCA $93,904 + Studio $6,578 = $3,868,675; non-trading = staked-SOL $116,119; total $3,984,794 → **97.1%**. Fees share: $8,931,939 / $11,122,849 = **80.3%** (LST fees are large relative to its revenue).
- **CAKE**: trading revenue = AMM $872,863 + AMM V3 $2,727,300 + StableSwap $554 + Infinity $271,504 = $3,872,222; prediction $263,790 + lottery $20,106 = $283,896 non-trading (but gambling, same casino family); total $4,156,117 → **93.2%** trading. Fees: $12,180,815 / $12,464,711 = **97.7%**.
- **HYPE**: perps + spot only; both methodologies say trading fees (perps also bundles AQAv2 reserve yield; spot also includes HIP-1 deployment auctions). No breakdown → share not numerically split; label casino because trading dominates.
- **AERO**: v1 fees include swap fees **plus bribes until 2026-10-22**; the 30-day window spans that period, so a clean trading-only percentage is not available. Label casino with the caveat, not a fabricated share.
- **Chains**: gas fees do not tell us whether the transaction was a swap, transfer, NFT mint or bridge; own-token trading cannot be separated. ETH revenue = burned base+blob fees; BSC revenue = 10% burned; SOL revenue = base fees burned; NEAR = 70% burned.

## Per-token sources (exact endpoints; dataType=dailyFees and dailyRevenue)

- ETH — https://api.llama.fi/summary/fees/ethereum — methodology: total ETH gas (base + priority + blob) paid by users; revenue = burned base/blob.
- BNB — https://api.llama.fi/summary/fees/bsc — BSC transaction fees; revenue = 10% burned. Binance CEX not included.
- SOL — https://api.llama.fi/summary/fees/solana — all transaction fees; revenue = base fees burned.
- NEAR — https://api.llama.fi/summary/fees/near — all gas fees; 70% burned, 30% to contract developers.
- TAO — no entry; direct calls to `summary/fees/bittensor` and `/tao` returned 400 and the fees overview has no Bittensor/TAO protocol. **Unknown, not guessed.**
- LINK — https://api.llama.fi/summary/fees/chainlink-requests — Requests + Keepers + VRF V1/V2 + CCIP fees; all LINK payments go to node operators (revenue 0). Staking is separate (`chainlink-staking`, $4.29M fees / $4.25M revenue 30d) and is a token/staking mechanism, not oracle usage; excluded to avoid mixing.
- HYPE — https://api.llama.fi/summary/fees/hyperliquid-perps and https://api.llama.fi/summary/fees/hyperliquid-spot-orderbook — perps and spot trading fees; revenue to Assistance Fund/buybacks.
- JUP — https://api.llama.fi/summary/fees/jupiter-aggregator, `/jupiter-perpetual-exchange`, `/jupiter-dca`, `/jupiter-studio`, `/jupiter-staked-sol`.
- RAY — https://api.llama.fi/summary/fees/raydium-amm — swap fees; revenue = treasury + RAY buybacks.
- ORCA — https://api.llama.fi/summary/fees/orca-dex — swap fees; 13% protocol share.
- PUMP — https://api.llama.fi/summary/fees/pump.fun and `/pumpswap` — bonding-curve/launchpad + AMM swap fees.
- UNI — https://api.llama.fi/summary/fees/uniswap-v2, `/uniswap-v3`, `/uniswap-v4` — swap fees; V3 revenue = UNI buyback/burn since Dec 2025.
- CAKE — https://api.llama.fi/summary/fees/pancakeswap-amm, `/pancakeswap-amm-v3`, `/pancakeswap-stableswap`, `/pancakeswap-infinity`, `/pancakeswap-prediction`, `/pancakeswap-lottery`.
- AERO — https://api.llama.fi/summary/fees/aerodrome-v1 and `/aerodrome-slipstream` — swap fees; v1 included bribes until 2026-10-22.

## Unknowns (explicit, never filled)

- Own-token trading share: **unknown for all 14** — the free DefiLlama fees API has no pair/transaction split.
- TAO: no fee/revenue series at all.
- ETH/BNB/SOL/NEAR: trading share of gas unknown; BNB's exchange business is outside DefiLlama.
- HYPE: reserve-yield and HIP-1 auction portions not separable.
- AERO: bribe portion of V1 fees not separable.
- LINK: `chainlink-requests` revenue is $0 (all to node operators). `chainlink-staking` revenue is separate and not counted above.
