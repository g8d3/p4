# e091 — Hooks Directory (hook projects across blockchains)

Goal: a web directory of projects building with hooks on different
blockchains — Uniswap v4 pool hooks (Ethereum/L2s), Token-2022 transfer
hooks (Solana), PancakeSwap Infinity hooks (BNB + multichain) — where every
listing is backed by a live X post found via twitterapis.com.

## Source

- API: `https://api.twitterapis.com` (note: NOT `twitterapi.io` — that host
  rejects this key). Auth header: `X-API-Key: $TWITTERAPIS_API_KEY`.
- Env var: `TWITTERAPIS_API_KEY` (already in environment, never in code).
- Queries run 2026-10-09, `queryType=Top`, `count=5–10`: "Uniswap v4 hooks",
  "Uniswap hook project launch", "hookathon uniswap", "Hookr hook blocks",
  "CLAUS v4 hook agent", "Rallypad hook launchpad", "Bunni v4 liquidity",
  "Solana transfer hook Token-2022", "PancakeSwap Infinity hook OR clAMM".
- User lookups via `/twitter/user/info?userName=` for follower counts + URLs.
- Query list + endpoint notes: `data/evidence.json`. Re-run: `bin/fetch.sh`.

## Structure

- `needs.json` — port/bind; only machine values file.
- `server/app.py` — stdlib only. Serves `/`, `/api/hooks`,
  `/api/evidence`, `/api/health`.
- `public/index.html` — REDO 2026-10-09 via `figma-implement-design` (followba SKILL.md,
  11513 bytes, read in full; same source as e089 v12). Design-handoff / inspect-panel
  aesthetic: filebar with file-key, 8px token scale, chain-color legend, per-frame node-ids
  (hook-01..hook-12), chain-swatch visual reference + fidelity line, inspect panel (search,
  chain segments, engine segments, sort), engine-grouped sections, Handoff QA footer.
  Zero external requests. Skill-source header comment leads the file.
- `data/hooks.json` — 13 listings (Bordrless added 2026-10-09 from 60-tweet Solana sample).
  Fields: name, handle, followers, chain[], hook_type, blurb, site, tweet_url, status, verified.
- `data/api.json` — 79 twitterapis.com endpoints with full param specs (filters, sorting,
  projection, cursors) extracted from docs 2026-10-09 + hand specs for prose-only POSTs.
  Explorer tab: pick endpoint, fill every documented param, Run (price shown, billed+logged),
  Next page via cursor, Save to evidence (merges + SQLite import). Writes confirm first.
  Custom-path mode covers the rest (articles, monitoring, grok). `/api/spec`, `/api/run`, `/api/save`.
  Query builder (2026-10-09): tweet-advanced-search shows a friendly form above the raw
  `query` box — words/phrase/any/exclude, hashtags, from/to/mention, lang, since/until,
  min likes/reposts/replies, filter + hide-replies/reposts checkboxes — with live preview,
  "Use this query ↓" to fill the box, Clear, 3 examples, and an operator cheat-sheet.
  No operator knowledge needed; raw box stays editable.
- `data/pairs.json` — top pair per project token (highest-liq live venue, 2026-10-09):
  HOOKR/V4 robinhood v4, CLAUS eth v2, HOOKED solana meteora, FLX eth v2, BORDR solana meteora.
  Served at `/api/pairs`. Cards embed it lazily: Chart-only vs Chart+Txs toggle + DexScreener link.
- `bin/fetch.sh` — paginated broad-query pattern (60 tweets × Solana/Uniswap/launchpad/Infinity).
  Lesson: broad Latest queries for discovery+freshness beat narrow Top queries (stale).
  Auto-logs each call to `data/usage.json` and re-runs `bin/import_evidence.py` at the end.
- `data/evidence.db` — SQLite (stdlib) with all 119 captured tweets (8 queries): id, query,
  dates+time, author, engagement counts, raw JSON. Built by `bin/import_evidence.py` (idempotent).
  `/api/tweet?id=` reads from it; `/api/tweets.csv` exports it. Raw `evidence/*.json` kept as backup.
- Sources tab: query chips filter the tab (✕ all to reset); per-tweet Request button shows the
  exact API request + engagement + ALL tweet fields + raw JSON; CSV download link included.
  Every tweet card shows engagement (likes/reposts/replies/quotes/views) and date+time inline —
  times render in the viewer's timezone via toLocaleString (ts_iso stored per hit).
- Credits widget (Sources tab): tracked spend from `data/usage.json` ($0.0008/read, fetch.sh auto-logs),
  dashboard balance (manual entry — no API exists for it, per docs), live rate-window probe
  ($0.0008 per check, 60s server cache).
- `data/signals.json` — score inputs, rebuilt 2026-10-09 after visiting all 10 project
  sites (tinyfish fetch). score = social(0-30, log followers+engagement+2000*authors)
  + traction(0-40, log OWN-TOKEN vol24 only) + freshness(0-20) + status(0-10).
  Roles: hook-infra (Hookr, Programmable, Fairlaunch) / dex (Infinity, Bunni) /
  launchpad (Rallypad, Hooked, Ballast, Permapad) / project (Claus, Unipeg) /
  program (UHI10). Host-dex vol (Infinity $190M, Bunni $0) shown as unscored context;
  launched-token vol without a public API is an explicit unscored_note. Social is
  mention-weighted (distinct authors + engagement on mention tweets), not followers alone.
  Limits documented: twitterapis.com gives no follower growth / impressions; site tables
  (Hookr markets, Rallypad markets, Ballast discover) have no public API — next step
  would be per-site scrapers or a volume indexer.
- `bin/serve.sh` — start server (reads port from needs.json).
- `bin/fetch.sh` — re-run twitterapis.com queries into `evidence/`.

## Coverage (2026-10-09)

- Uniswap v4 (EVM): Hookr, Bunni v2, Claus, Programmable, Rallypad,
  Fairlaunch (dual-engine), Unipeg, Ballast, UHI10 hookathon prototypes.
- Solana (Token-2022): Hooked/Hoookedpad.
- BNB/multichain (Infinity): PancakeSwap Infinity.
- Robinhood Chain: Permapad / Diamond Hand Hook.

## Caveats

- Chains for small EVM projects = Uniswap v4 deployment footprint, not
  per-project confirmations; verify beforeLP/buy.
- Bunni v2: $8M+ LDF exploit Sep 2025 — flagged on card.
- Follower counts are point-in-time (tweet day), not a rank.

## Inherits
- [../AGENTS.md](../AGENTS.md) — standing rules (live IPs, user-seat review,
  config from needs.json, kill by exact PID).
