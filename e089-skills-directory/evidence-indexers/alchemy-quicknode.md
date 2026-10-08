# Alchemy + QuickNode Streams — evidence (2026-10-08)

## Sources
- https://www.alchemy.com/pricing (official pricing)
- https://www.alchemy.com/overviews/alchemy-vs-quicknode (official comparison, Sept 2024 24h snapshot — biased source)
- https://www.quicknode.com/streams (official Streams page)
- https://www.quicknode.com/pricing (official pricing)
- https://chainstack.com/alchemy-rpc-provider-overview-2026/ (third-party overview)

## Quotes
- "Start free with 30M compute units per month. Pay as You Go at $0.525/1M CU. Enterprise plans with custom SLAs and dedicated support across 100+ chains." (alchemy.com/pricing via snippet)
- "Alchemy offers a free plan that includes up to 30 million Compute Units per month, which translates to roughly 1.8 million simple RPC requests..." (chainstack)
- "Average latency. 15.69 ms. 55.69 ms... P50 latency. 6.32 ms. 9.70 ms." — Alchemy vs QuickNode per Alchemy's own benchmark (biased; needs independent verification).
- "Up to 6 destinations on Enterprise, no duplicate streams, no extra cost." (quicknode.com/streams via snippet)
- "Quicknode's infrastructure is optimized for low latency and high throughput, handling over 200 billion API requests monthly with a 99.99% uptime SLA..." (quicknode builders-guide via snippet)

## Facts
- Alchemy chains: 100+ (per pricing page). QuickNode chains: multi-chain (count not captured — verify).
- Latency/freshness: RPC request/response (ms-scale) + webhooks/Notify (Alchemy) / Streams to multi-destinations (QuickNode).
- Pricing: Alchemy = compute-unit model (30M CU/mo free; $0.525/1M CU pay-as-you-go; enterprise custom). QuickNode = tiered plans (tiers not captured — verify on pricing page).
- Decentralization: both hosted infra providers.
- Query interface: RPC + REST token/NFT/transfer APIs + webhooks/streams; Alchemy JS SDK (alchemy-sdk — well-known, verify version).
- Self-host: no for both.
