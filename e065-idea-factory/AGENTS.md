# e065 — Idea Factory (likes/bookmarks → build ideas)

Mines e064's X snapshot into build ideas, continuously. Runs every
30-min leg right after e064: clusters recurring themes by frequency,
brainstorms BEYOND the source material, and publishes a ranked table.
Second link: e064 (signal) → e065 (ideas) → e066 (builds).

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, quiet mode
- [../e062-agent-ops/DIRECTIVES.md](../e062-agent-ops/DIRECTIVES.md) — runner rules, reporting format
- [../AGENTS.md](../AGENTS.md) — experiment index

## Goal

Each leg reads `../e064-x-bookmarks/output/latest.json` and rewrites
`output/ideas.md`: a TABLE with one row per idea —
`| idea | evidence (n likes/bookmarks) | novelty | effort | score |`.
Rules:

- Rank by frequency of the theme in likes/bookmarks AND by novelty.
- At least 1 genuinely new idea per leg that is NOT a paraphrase of a
  liked post (brainstorm beyond the feed — combine, invert, transplant
  to another chain/market).
- Keep `output/history/` append-only (one file per leg, ignored ok) so
  idea frequency becomes a time series; surface rising themes.
- e066-verification: when the feed talks about something big (e.g. the
  Arc chain launch chatter, Sep 2026), it MUST appear here first with a
  build proposal — that is how the owner verifies this factory works.

## Proof number

New viable ideas banked per leg + share of ideas already picked up as
builds. Beat tech half ends with `score ideas=<new_this_leg>`.

## DONE ladder

1. WORKING — `ideas.md` table regenerates from live e064 data.
2. DEPLOYED — refreshes on the 30-min runner.
3. TESTED — spot-check: top-3 rows traceable to source post URLs.
4. ANNOUNCED — owner ping when a rising theme crosses threshold.
5. MONETIZED — never (internal pipe; the BUILDS monetize, e.g. e066).
