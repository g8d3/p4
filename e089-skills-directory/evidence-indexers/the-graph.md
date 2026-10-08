# The Graph — evidence (2026-10-08)

## Sources
- https://thegraph.com/studio-pricing/ (official pricing)
- https://thegraph.com/docs/en/indexing/overview/ (official docs)
- https://costbench.com/software/blockchain-data-api/the-graph/ (pricing summary)

## Quotes
- "Start accessing blockchain data with 100,000 free monthly queries. Need more data? Keep going for just $2 per 100,000 queries." (studio-pricing)
- "Unlimited Subgraph creation / Dedicated indexing / Unlimited testing / Usage-based billing" (studio-pricing)
- "Instantly access blockchain data on 60+ networks." (studio-pricing)
- "Developers use Subgraphs to define their schema, and a set of mappings for transforming the data sourced from the blockchain and the Graph Node handles syncing the entire chain, monitoring for new blocks, and serving it via a GraphQL endpoint." (docs)
- "The Graph pricing starts with a Free Tier at $0/month... For production workloads, the Pay-Per-Query plan scales with usage at custom rates set by the decentralized network." (costbench)

## Facts
- Chains: 60+ networks (per official site).
- Latency/freshness: subgraph sync + block-following queries; Substreams for streaming (flagship streaming primitive, widely documented — verify version).
- Pricing: usage-based, 100k queries/mo free, then $2 per 100k.
- Decentralization: decentralized network, paid in GRT; Studio traffic migrating from centralized staging to decentralized network (per CoinMarketCap AI brief, BNB/Polygon deadline Oct 2026 — secondary source, verify).
- Query interface: GraphQL (per-subgraph endpoints).
- Self-host: yes — Graph Node is open source, anyone can run a node (long-standing fact; verify current docs link).
