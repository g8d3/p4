# Proposed column set for the blockchain-data-indexer directory (2026-10-08)

Rule: one fact per column, every column filterable or sortable. 10 columns.

| # | Column | Type | Values / unit | Why it matters for picking one |
|---|--------|------|---------------|-------------------------------|
| 1 | name | text (sort) | product name | Identity; anchor for search. |
| 2 | type | enum (filter) | `app-subgraph` · `indexer-framework` · `unified-data-api` · `rpc-stream` · `sql-warehouse` | The single biggest fork in the decision: custom per-app indexing (Graph, Envio, Ponder, Apibara, Checkpoint, SQD) vs plug-and-play APIs (GoldRush, Moralis, Alchemy) vs streaming infra (QuickNode Streams, Helius LaserStream) vs analytics warehouses (Dune, Flipside, Bitquery warehouse). |
| 3 | chains_count | number (sort) + `chains_note` text | e.g. 100+; note names flagship chains | Filters out products that don't cover your chain (e.g. Helius = Solana specialist vs GoldRush 100+). Count sorts; note keeps it honest. |
| 4 | query_interface | multi-enum (filter) | `graphql` · `sql` · `rest` · `rpc` · `websocket` · `webhook` | Determines integration cost: frontend teams want GraphQL/REST, analysts want SQL, backends want streams/webhooks. Multi-select because most products offer 2+. |
| 5 | latency | enum (filter+sort) | `streaming` (sub-second) · `near-real-time` (seconds) · `indexed` (block-following/minutes) · `warehouse` (batch) | Freshness decides use-case fit: trading bots need streaming (Bitquery streams, LaserStream, QuickNode Streams); dashboards tolerate indexed/warehouse (Dune, Flipside). |
| 6 | pricing_model | enum (filter) | `per-query` · `credits-subscription` · `compute-units` · `self-host-free` · `seats` | Predicts bill shape: usage meters (Graph $2/100k queries, Alchemy CU) vs flat subscriptions (Bitquery $49/$99/$299, Helius tiers) vs $0 self-host (Ponder, Checkpoint). |
| 7 | free_tier | bool (filter) + `free_note` text | e.g. true — "100k queries/mo" | Tells a builder whether they can prototype without a card: Graph 100k/mo, Alchemy 30M CU/mo, Helius 1M credits, GoldRush 14-day/25k credits, Dune 2.5k credits/mo. |
| 8 | decentralization | enum (filter) | `decentralized-network` · `oss-self-host` · `hosted` | Trust + lock-in axis: Graph/SQD run decentralized networks; Envio/Ponder/Apibara/Checkpoint are OSS you run yourself; GoldRush/Moralis/Alchemy/QuickNode/Helius/Dune/Flipside/Bitquery are hosted SaaS. |
| 9 | self_host | bool (filter) + `selfhost_note` text | e.g. true — "open-source, runs on Node.js" | The exit option: Ponder/Envio/SQD/Apibara/Checkpoint = yes; all SaaS APIs = no. Decides whether you can escape vendor infra. |
| 10 | verified + source_url | date (sort) + url | evidence file link + fetch date | Every fact expires (pricing changes quarterly). Storing the source + date per row is what makes the directory trustworthy instead of stale. |

## Deliberately excluded
- SDKs language list — merged into `query_interface` notes; a separate column adds width without filtering power (almost all offer JS/TS+Python).
- Token/Network detail — folded into `decentralization` notes; only Graph/SQD/Chainbase/Covalent have token angles and it rarely decides selection.
- Uptime/SLA — vendor-claimed, not independently verifiable from marketing pages; would need active probing (future leg).

## Coverage gaps to close before building (marked VERIFY in evidence files)
1. Chainbase: pricing, latency model, chain count, self-host — needs docs+pricing fetch.
2. Moralis: exact tiers, chain count, SDK list — needs pricing-page fetch.
3. QuickNode: plan tiers, chain count — needs pricing-page fetch.
4. Apibara: hosted-cloud pricing, exact chain list — needs docs fetch.
5. Ponder: served API surface (GraphQL? Postgres-direct?) — needs docs fetch.
6. Latency SLAs for all hosted APIs — vendor claims only; consider labeling as `claimed`.
