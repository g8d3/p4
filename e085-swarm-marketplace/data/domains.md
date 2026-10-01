# Domain scout — swarm marketplace (e085)

Scout: domain-scout. Date: 2026-10-01. **Nothing purchased** (RDAP read-only checks only).
Method: `curl -sL https://rdap.org/domain/<name>` — HTTP 404 = likely free, HTTP 200 = taken.
Cross-checked 2 names against the in-app checker (`GET /api/domain-check`): both agree ✔.

> Porkbun prices below are **guesses** (Porkbun lists .cc ≈ $10/yr, .com ≈ $11/yr at time of writing).
> Confirm live at checkout — prices and availability change. RDAP absence is not a guarantee.

## Ranked table (free first, then short, then brandable)

| # | Domain | Theme | Chars* | RDAP | In-app `/api/domain-check` | Porkbun guess | Note |
|---|---|---|---|---|---|---|---|
| 1 | swarmly.cc | swarm | 7 | 404 likely free | `available: true` ✔ | ~$10/yr .cc | ⭐ Top pick: shortest, brandable, adverb-style |
| 2 | swarmloop.cc | swarm+loop | 9 | 404 likely free | — | ~$10/yr .cc | Loop theme, says "marketplace flywheel" |
| 3 | hiveloop.cc | hive+loop | 8 | 404 likely free | — | ~$10/yr .cc | Hive theme, close second |
| 4 | fleetloop.cc | fleet+loop | 9 | 404 likely free | — | ~$10/yr .cc | Fleet theme, good for rent-a-fleet angle |
| 5 | swarmbay.cc | swarm | 8 | 404 likely free | — | ~$10/yr .cc | "Bay" = marketplace signal (eBay-style) |
| 6 | hivebay.cc | hive | 7 | 404 likely free | — | ~$10/yr .cc | Shortest + marketplace signal |
| 7 | swarmfleet.cc | swarm+fleet | 10 | 404 likely free | — | ~$10/yr .cc | Descriptive, slightly long |
| 8 | hivefleet.cc | hive+fleet | 9 | 404 likely free | — | ~$10/yr .cc | Descriptive, solid fallback |
| 9 | swarmloop.com | swarm+loop | 9 | 200 TAKEN | `available: false` ✔ | ~$11/yr IF free (n/a) | Ideal .com is gone — .cc twin (#2) is free |
| 10 | hiveloop.com | hive+loop | 8 | 200 TAKEN | — | ~$11/yr IF free (n/a) | Ideal .com is gone — .cc twin (#3) is free |

\* Chars = second-level label length (before the dot).

## Also probed (taken, not ranked)

`fleetloop.com`, `swarmfleet.com`, `hivefleet.com`, `loopswarm.com`, `fleetly.cc` → all RDAP 200 (taken).
Pattern: every obvious `.com` in this theme space is registered; the entire `.cc` twin set was 404 at check time.

## Recommendation

Register **swarmly.cc** (shortest, most brandable, likely <$15/yr). Backups: **swarmloop.cc**, **hiveloop.cc**.
Re-check RDAP + Porkbun at purchase time before committing (availability moves fast).
