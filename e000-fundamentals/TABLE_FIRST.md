# TABLE_FIRST — shared rule for all p4 experiments

Status: shared convention (opt-in via `## Inherits`, one line per project).
No copies: projects link here, they never duplicate this file.

## The rule

Every fact lives in a table with named columns. The page renders tables.
Free-floating text (walls of text) is forbidden, except one verdict line.

## What this means (5 checks)

1. **Real rows, not JS promises.** The served HTML must contain data `<tr>`
   rows outside `<script>` blocks. An empty `<table id="t"></table>` that
   only fills in via JS fetch = FAIL (`NO_TABLE`). Counters lie, rows don't.
2. **Counter + pagination.** The page shows the total (`N rows`) AND paginates
   (page 1/N, next/prev, or per-page control). Never dump all rows at once on
   mobile. Counter without pagination = FAIL. Pagination without counter = FAIL.
3. **Growth.** Rows AND columns must grow over time from new sources.
   The check reports `rows=<n> cols=<m>` from the CSV/JSON so a new session
   sees in one line whether the table got richer since yesterday.
4. **Atomic numeric columns.** One fact per column, numbers as numbers.
   A cell like `110.73, 0.1x L1 median, getting pricier, thru 2026-09-12`
   is 4 facts in 1 string = FAIL (`MIXED_CELL`). Split it: `p_fees=110.73`,
   `vs_median=0.1`, `trend=+1`, `through=2026-09-12`. SQL must work on every
   column without parsing text.
5. **Time first.** Every row carries a date (`through`). The page badge and
   pulse must reflect the OLDEST date, not the newest. Prefer sources that
   already carry history (no waiting 30 days to build a series). Claiming
   `LIVE`/`through <max>` while `min < max` = FAIL (`STALE_MASK`).

## Text-wall limit

Numbers outside `<table>` (verdict/pulse/score/alerts divs) must be fewer
than numbers inside `<table>`. More numbers outside than inside = FAIL
(`TEXT_WALL`): move the facts into columns with labels.

## How to adopt (one line, no context bloat)

Add to the experiment's `AGENTS.md`:

```markdown
## Inherits
- [../../e000-fundamentals/TABLE_FIRST.md](../../e000-fundamentals/TABLE_FIRST.md) — table-first rule + table_check.py
```

Run the check (seconds, offline, few tokens):

```bash
python3 ../e000-fundamentals/bin/table_check.py e059-crypto-valuations
```

New sessions run this FIRST, before reading any code.

Implementation: do not hand-roll tables — use
[e068-tablelib/](../e068-tablelib/AGENTS.md), which complies by construction.
