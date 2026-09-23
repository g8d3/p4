#!/usr/bin/env python3
"""e071 sources: directory of every data source feeding the tables.

Static curation + live status flags -> output/sources.json, rendered as the
Sources tab. Live = queried by refresh.sh. Manual = curated link/override.
Planned = not wired yet (needs key or contract work); kept visible so gaps
are explicit instead of silent nulls.
"""
import json, os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")

ROWS = [
    {"source": "DexScreener", "kind": "market data", "url": "https://dexscreener.com",
     "access": "keyless", "cadence": "every refresh",
     "covers": "price/mcap/fdv/vol24/liq/txns/pair birth (solana+base+robinhood)",
     "status": "live", "note": "tokens/v1 per chain+mint; multi-chain lookup resolved RH=robinhood"},
    {"source": "CoinGecko API", "kind": "market data", "url": "https://coingecko.com",
     "access": "keyless public", "cadence": "every refresh",
     "covers": "majors quotes/ATH/ATL/supply (TAO/VVV/ROUTER/DOT); SOL price for SQUIRE sales proxy",
     "status": "live", "note": "coins/markets + coins detail (cached 24h); genesis_date null -> curated overrides"},
    {"source": "GeckoTerminal", "kind": "history", "url": "https://geckoterminal.com",
     "access": "keyless", "cadence": "full loop 2x/day",
     "covers": "day-OHLCV -> ATH/ATL/dates/sig-low/30d spark; normalized supply",
     "status": "live", "note": "supports robinhood network"},
    {"source": "Solana RPC", "kind": "supply", "url": "https://api.mainnet-beta.solana.com",
     "access": "keyless", "cadence": "full loop 2x/day",
     "covers": "getTokenSupply -> supply_total fallback",
     "status": "live", "note": ""},
    {"source": "Base RPC", "kind": "supply", "url": "https://mainnet.base.org",
     "access": "keyless", "cadence": "full loop 2x/day",
     "covers": "eth_call totalSupply/decimals -> supply_total fallback",
     "status": "live", "note": ""},
    {"source": "CoinMarketCap", "kind": "review links", "url": "https://coinmarketcap.com",
     "access": "manual slugs", "cadence": "on universe change",
     "covers": "cmc_url column for majors (verified 200s 2026-09-22)",
     "status": "live", "note": "no keyless API; links only, never numbers"},
    {"source": "CoinGecko pages", "kind": "review links", "url": "https://www.coingecko.com",
     "access": "manual ids", "cadence": "on universe change",
     "covers": "coingecko_url column for majors",
     "status": "live", "note": "links only, never numbers"},
    {"source": "gmgn.ai", "kind": "review links", "url": "https://gmgn.ai",
     "access": "manual pattern", "cadence": "on universe change",
     "covers": "gmgn_url column for solana/base mints (no robinhood support)",
     "status": "live", "note": "links only, never numbers"},
    {"source": "X threads", "kind": "universe seed", "url": None,
     "access": "manual", "cadence": "static",
     "covers": "token list + tiers + seed quotes (@Shawred0 @sal_ash_ @entyper 2026-09-19/21)",
     "status": "live", "note": "seeds superseded by live feeds; kept as fallback"},
    {"source": "Curated genesis", "kind": "age override", "url": None,
     "access": "manual", "cadence": "on universe change",
     "covers": "born_ts/age_days for majors (TAO 2021-01-09, VVV 2025-01-27, DOT 2020-05-26)",
     "status": "live", "note": "web-verified 2026-09-22; ROUTER null (uncertain row, no fabrication)"},
    {"source": "Dune Analytics", "kind": "revenue/usage", "url": "https://dune.com",
     "access": "needs API key", "cadence": "unwired",
     "covers": "per-project inference revenue + usage -> real P/S, sales_share, usage_share",
     "status": "planned", "note": "would replace SQUIRE-only sales proxy"},
    {"source": "Block explorers", "kind": "verify", "url": None,
     "access": "keyless w/ limits", "cadence": "unwired",
     "covers": "birth/supply cross-check (BaseScan, taostats, Subscan, Robinhood explorer)",
     "status": "planned", "note": "Robinhood-chain explorer URL still to resolve"},
    {"source": "Vesting docs", "kind": "unlocks", "url": None,
     "access": "manual", "cadence": "unwired",
     "covers": "unlock_next_ts/pct -> unlocks.json (currently empty)",
     "status": "planned", "note": "tokenomics docs + vesting contracts per project"},
]

def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_ts = int(datetime.now(timezone.utc).timestamp())
    out = {"as_of": now, "server_ts": now_ts, "n": len(ROWS), "rows": ROWS,
           "note": "every feed behind a table cell, live or explicitly planned"}
    tmp = os.path.join(OUT, "sources.json.tmp")
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, os.path.join(OUT, "sources.json"))
    live = sum(1 for r in ROWS if r["status"] == "live")
    print(f"sources ok: {len(ROWS)} entries, {live} live")

if __name__ == "__main__":
    main()
