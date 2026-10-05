# e087 — OSS Launchpad Scout (skills-first, trends-driven)

Goal: user asked for a new experiment that (1) searches and TESTS many
web-dev-related skills (past web apps were poor), (2) picks the web app idea
from real X.com trends (not invented), with verifiable network access
(no hallucination, no giving up), oriented to: Solana + launchpads +
funding-rate arbitrage + videogames + gambling/skill games + AI agents +
open-source monetization, (3) monetized BOTH ways: fiat merchant-of-record
AND crypto, (4) expands OSS monetization: unmonetized OSS repos get
monetized, money back to contributors, plus an easy token launchpad where
anyone creates a token backed by 1+ OSS projects monetized via AI agents —
buyers support contributors and share profits.

## Method (skills before app, trends before idea)

- Phase 0 — Skill inventory + live tests. Catalog every usable web-dev
  skill visible from this repo (p4/skills, ~/.pi skills, pi-web packages,
  opencode bridge, etc.). Each skill gets a real execution probe, not a
  README summary. Score: works / partial / broken. See `skills/catalog.md`.
- Phase 1 — Network-access proof. For each net skill (use-tinyfish,
  browser-extract, terminal-browser, web_search/web_fetch equivalents)
  run a live probe against a known URL + an X.com URL, save raw output in
  `evidence/`. Rule: no trend claim without saved raw evidence.
- Phase 2 — X trend scout. Topics: solana, launchpads, funding arb,
  videogames, gambling/skill, AI agents, OSS monetization. Each finding =
  URL + timestamp + raw quote/screenshot ref. User verifies ("eso está
  correcto") before we lock the app idea.
- Phase 3 — App proposal + prototype only AFTER user confirms trends.
  Dual monetization (fiat MoR + crypto) and OSS-token launchpad mechanics
  designed here, not before.

## Inherits

- ../e041-web-access-agents/AGENTS.md — web access stack, no silver bullet
- ../e057-launchpad-tokens, ../e057-launchpad-trading, ../e058-funding-scanner,
  ../e060-social-memecoin-radar, ../e061-game-launchpad-suite — prior art, reuse
- ../e050-ponytail — laziest working solution for the prototype

## Structure

```
e087-oss-launchpad-scout/
├── AGENTS.md
├── needs.json            # machine values (ports/paths/URLs) — never hardcoded elsewhere
├── skills/catalog.md     # Phase 0 results
├── evidence/             # Phase 1 raw probes (net-proof)
├── trends/               # Phase 2 raw findings (one file per topic)
├── public/index.html     # Phase 3 prototype (only after trend lock)
├── server/app.py         # Phase 3 prototype API (stdlib only)
├── bin/                  # probe/scout scripts
└── DECISION.md           # locked app idea (written only after user confirms trends)
```

## Rules

- No app code before DECISION.md exists and user said trends are correct.
- Every network claim links to a file in evidence/ or trends/ with URL + date.
- Standing rules apply: live IPs/URLs each server turn, user-seat review,
  config from needs.json, kill by exact PID.
