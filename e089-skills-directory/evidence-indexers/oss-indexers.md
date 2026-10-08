# Self-hostable OSS indexers: Subsquid + Envio + Ponder + Apibara + Checkpoint — evidence (2026-10-08)

## Sources
- https://sqd.dev/ (official) + https://sqd.dev/compare/sqd-vs-envio/ (official comparison — biased)
- https://docs.envio.dev/docs/HyperIndex/overview + https://docs.envio.dev/docs/HyperIndex/hosted-service-billing (official docs)
- https://docs.envio.dev/blog/best-blockchain-indexers-2026 (official benchmark post — biased, covers Envio, Graph, Goldsky, SubQuery, SQD, Ormi, Ponder)
- https://ponder.sh/ (official, fetched 2026-10-08)
- https://www.apibara.com/ (official, fetched 2026-10-08)
- https://github.com/snapshot-labs/checkpoint (official repo)
- https://ethereum.org/developers/tools/checkpoint-snapshot-labs/ (third-party listing)
- https://reports.tiger-research.com/p/subsquid-eng (third-party research)

## Quotes
- "The entire stack is open-source... Self-host on your own infra anytime. Battle-tested at scale." (sqd.dev via snippet)
- "Subsquid (hereafter SQD) simplifies blockchain data access through decentralized infrastructure. It supports over 200 blockchains..." (tiger research via snippet)
- "Free public Portal tier; no token to run. Required: indexers read from HyperSync, which needs an Envio API token; Envio Cloud-hosted indexers are exempt..." (sqd-vs-envio — biased, verify on Envio docs)
- "HyperIndex is a blazing-fast, developer-friendly multichain indexer, optimized for both local development and reliable hosted deployment." (envio docs)
- "HyperIndex can be self-hosted, and it can also run on Envio Cloud, a fully managed hosting service..." (envio.dev/compare via snippet)
- "Envio Cloud offers flexible pricing plans to match your project's needs, from free development environments to enterprise-grade dedicated hosting." (envio billing docs via snippet)
- "Ponder is an open-source TypeScript framework for fast, reliable, and maintainable EVM data indexing... Deploy anywhere that runs Node.js with zero downtime & horizontal scaling" (ponder.sh, fetched)
- "Ponder indexes 100x faster than The Graph" — Ponder's own benchmark (Rocket Pool ERC20, mainnet blocks 18.6M–18.7M: 37s vs 5m28s cold sync; biased, self-reported, verify methodology before repeating as fact).
- "Apibara is the fastest platform to build production-grade indexers that connect onchain data to web2 services... Apibara is open source... Self-hosted DNA" (apibara.com, fetched; DNA = Direct Node Access, gRPC streaming straight from node)
- "Checkpoint is a library for indexing data of StarkNet contracts and making it accessible through GraphQL. Checkpoint is inspired by The Graph..." (github snapshot-labs/checkpoint via snippet)
- "Checkpoint from Snapshot Labs is a library for indexing Ethereum and Starknet contract events and serving them over GraphQL." (ethereum.org listing)

## Facts
- Subsquid/SQD: modular batch-indexing SDK + distributed archive data lake + decentralized Subsquid Network; 200+ chains (per tiger research); open-source, self-hostable; GraphQL queries; free public Portal tier (per competitor page — verify).
- Envio HyperIndex: multichain, any-EVM indexer; open-source, self-hostable; Envio Cloud hosted (free dev envs → enterprise); reads via HyperSync (API token; Cloud-hosted exempt); GraphQL.
- Ponder: open-source TypeScript EVM framework; self-host anywhere Node.js runs ($0 infra = your own); no first-party cloud (verify); serves app APIs over Postgres (GraphQL — verify exact API surface on docs).
- Apibara: open-source; self-hosted DNA (gRPC direct-from-node streaming); Starknet + EVM (exact chain list — verify); TypeScript SDK (defineIndexer) + Postgres sinks (Drizzle); hosted cloud offering exists (per Starknet blog — verify pricing).
- Checkpoint: Snapshot Labs library; Ethereum + Starknet contract events → GraphQL; open-source, self-run (it's a library, not a network); $0 (your own infra).
- Decentralization: SQD = decentralized network; Envio/Ponder/Apibara/Checkpoint = open-source + self-host (centralization = wherever YOU run them).
