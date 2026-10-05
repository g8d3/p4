# TinyFish probe — RAW output

Date (UTC): 2026-10-05T14:54:49Z
Host: local agent shell, `tinyfish` CLI on PATH.
Purpose: prove `tinyfish search` + `tinyfish fetch` reach the live internet.

## 1. Search (exact command + full pretty output)

Command:

```bash
tinyfish search query "solana launchpad september 2026" --pretty
```

Raw output (untruncated — 7 results):

```text
Query: solana launchpad september 2026
Total results: 7
Page: 0

1. Best Solana Launchpad 2026: 8 Platforms Compared | Alchemii
   https://www.alchemii.io/blog/best-solana-launchpad-2026
   Best Solana Launchpad 2026: 8 Platforms Compared 8 Solana launchpads scored on cost, authority control, LP integration and trust signals. alchemii finishes first at 30/35. Full per-axis table.

2. Best Solana Launchpads 2026: Top Picks for Launches and Early ...
   https://cryptoslate.com/launchpads/solana-launchpads/
   A ranked comparison of the best Solana launchpads in 2026, covering setup requirements, costs, and bot/sniper protection for each platform.

3. Best Solana Launchpads 2026 — Pump.fun vs LetsBonk, Bags ...
   https://madeonsol.com/compare-launchpads
   If you launch tokens seriously, also see our deployer intelligence tools. Which Solana launchpad is the biggest in 2026? + Pump.fun. It reclaimed the lead after LetsBonk's mid-2025 surge and remains the largest by launch volume, with PumpSwap among the highest-volume Solana AMMs. LetsBonk is the strongest challenger.

4. Solana Changelog: September 10, 2026 | Solana Media
   https://solana.com/news/solana-changelog-september-10-2026
   Solana Changelog: September 10, 2026 This is a weekly newsletter on the latest Solana engineering news this week. If you want to stay updated on Solana tech every week, follow Solana Changelog at @solana_devs and @readylayerone and turn on notifications. Major Network Announcement: Please check your applications to see if they support V1 ...

5. Best Solana Launchpad 2026: 7 Platforms Ranked by Use Case
   https://solfoundry.io/blog/best-solana-launchpad-2026
   The best Solana launchpad in 2026 depends on your launch. Honest rankings for speed, sniper protection, creator fees, and trust — Pump.fun, LetsBonk, Heaven, Bags ...

6. Alpenglow | Solana Media
   https://solana.com/upgrades/alpenglow
   Alpenglow Updated September 2026 • Solana Foundation Alpenglow is Solana's next consensus upgrade. Consensus is how the validators that run Solana agree on the order of transactions and on when a transaction can no longer be reversed. Today that takes about 12.8 seconds. Alpenglow targets roughly 150 milliseconds. For most people the effect is simple: transactions settle almost immediately ...

7. Best Solana Launchpads in 2026: Pump.fun vs LetsBONK vs ...
   https://graphdex.io/en/blog/best-solana-launchpads-2026
   IMC narrative tokens Social launch mechanics Best Solana launchpads 2026 market share — Pump.fun vs LetsBONK vs Meteora Pump.fun: The Original Fair-Launch Pioneer Best for:Memecoin traders who want the deepest liquidity and most launches Pump.fun is a Solana launchpad where anyone can create a token instantly for about 0.01 SOL. It uses a bonding curve to set prices and locks liquidity ...
```

Exit code: 0.

## 2. Fetch result #1 (exact command + raw JSON, truncated at 8000 chars)

Command:

```bash
tinyfish fetch content get --format markdown "https://www.alchemii.io/blog/best-solana-launchpad-2026"
```

Raw output (first 8000 chars of JSON; full text continues server-side, not shown here):

```json
{"results":[{"url":"https://www.alchemii.io/blog/best-solana-launchpad-2026","final_url":"https://www.alchemii.io/blog/best-solana-launchpad-2026","title":"Best Solana Launchpad 2026: 8 Platforms Compared","description":"8 Solana launchpads scored on cost, authority control, LP integration and trust signals. alchemii finishes first at 30/35. Full per-axis table.","language":"en","author":"Gary Zhao","published_date":"2026-05-28","latency_ms":346.19,"format":"markdown","text":"# Best Solana Launchpad 2026: 8 Platforms Compared\n\n8 Solana launchpads scored on cost, authority control, LP integration and trust signals. alchemii finishes first at 30/35. Full per-axis table.\n\nReady to create your Solana token? Enter your token details, choose your authority options, and confirm in your wallet.\n\nThe best Solana launchpad in 2026 is alchemii, which finishes top of this scorecard at 30 of 35 on the operator axes — four points clear of the next platform. It takes the maximum score on authority control, LP integration, trust signals at deploy, post-launch tooling, and a flat fee charged once that never touches your trading volume. [...]"}]}
```

Note: `--pretty` variant of the same fetch returned only the header
(`Results: 1 / Errors: 0 / Title: ...`) without body text — the JSON
(non-pretty) form above is the one that carries the article text.
`--pretty` fetch Drill: body is NOT included; use default JSON for evidence.

## 3. Fetch result #3 (exact command + raw JSON head)

Command:

```bash
tinyfish fetch content get --format markdown "https://madeonsol.com/compare-launchpads"
```

Raw output head (latency_ms ≈ 15203, i.e. slow but succeeded):

```json
{"results":[{"url":"https://madeonsol.com/compare-launchpads","final_url":"https://madeonsol.com/compare-launchpads","title":"Best Solana Launchpads 2026 — Compared","description":"Pump.fun vs LetsBonk, Moonit, Bags, Believe, Boop.fun & DAOs.fun — graduation venue, fees, creator revenue and fiat on-ramp side-by-side.","language":"en","author":null,"published_date":null,"latency_ms":15203.88,"format":"markdown","text":"Last updated: September 2026\n\nCompare · Solana launchpads\n\n# Where your token actually launches.\n\nPump.fun vs LetsBonk, Moonit, Bags, Believe, Boop.fun and DAOs.fun — the launchpads that mint most of Solana's tokens, compared on the things that actually matter: where they graduate, what they charge, and how much creators keep. [...]"}]}
```

Key facts visible in fetched body (for Phase 2 reuse, not a trend claim):
- Pump.fun reclaimed the lead after LetsBonk's mid-2025 surge; graduates at ~85 SOL to PumpSwap.
- Moonit (Moonshot) shows a maintenance page since ~Aug 2026 — check before relying on fiat on-ramp.
- Page states "Last updated: September 2026".

## Verdict for this pipe

`tinyfish search` → WORKS (7 ranked results, exit 0).
`tinyfish fetch content get` → WORKS on normal SSR/marketing pages
(alchemii.io, madeonsol.com), exit 0, real article text returned.
`--pretty` fetch hides the body — evidence must use default JSON output.
