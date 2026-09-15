# TABLE_UX — shared UX rules for every p4 table page

Status: shared convention (opt-in via `## Inherits`, same as TABLE_FIRST.md).
TABLE_FIRST.md = the data exists and is honest. This file = the user can
READ it and USE it with minimum taps. Both gates run in `bin/table_check.py`
(Tier 1 = FAIL, Tier 2 = WARN).

## U1. Pills and badges must be readable in BOTH themes

The bug: a `thin n=10` pill with light-yellow background but NO explicit
text color. In dark mode the text inherits near-white body color →
white-on-pale-yellow, unreadable. It passed e2e because grep cannot see color.

Rules:
- Every pill/badge class (`.thin`, `.badge`, `.stale`, any new one) declares
  BOTH `background` AND `color` explicitly. Never inherit text color on a
  colored background.
- Every pill declares an `html.dark` variant. Light theme is not the test;
  the phone in dark mode is.
- Contrast ratio text-vs-background ≥ 4.5 (WCAG AA) in both themes.
- The checker computes it from the CSS. New pill without both properties
  = WARN `PILL_CONTRAST`.

## U2. The user configures columns, not the agent

The bug: a wide table on a narrow phone — one column cut off-screen while
another column wastes half its width on empty space. The agent chose a fixed
layout; the user cannot fix it.

Rules:
- The user controls: which columns are visible, column order, and density
  (simple/full). Choices persist (`localStorage`).
- On narrow screens the table MUST offer a vertical (transposed/card) layout:
  each row becomes a labeled card, no horizontal scrolling to find a value,
  no cut-off columns, no giant empty cells.
- A fixed wide table with cut columns + wasted space = WARN `COLUMN_LAYOUT`.

## U3. Every table carries its own SQL — zero wasted taps

The bug: filters live in a bar far from the table, page size is fixed, and
sorting means finding another control. Each analysis costs the user 3–5 taps
that the table itself could have served in 1.

Rules (per table, inline, not in a distant toolbar):
- Tap a column header = sort by it (tap again = reverse). All sortable
  columns, including computed ones.
- Filter INSIDE each column header (text input, min+max range, or select),
  not in a top bar. The user filters where the values are. Uniform by
  default: every sortable column has its filter (opt-out with `nofilter`,
  never by accident — ragged filters = WARN `RAGGED_FILTERS`).
- Page-size selector next to the pager (`10 / 25 / 50 / all`), not a fixed
  constant. The user decides the trade-off, per table.
- Group-by + computed columns where the page already computes them
  (medians, ratios, sparklines): one tap to group, no new page.
- Choices persist per table (`localStorage`). Missing pieces surface as
  WARNs, one per gap: `NO_SORT_HEADERS`, `NO_COLUMN_FILTERS`, `NO_PAGE_SIZE`.
- Control model (thumbbar vs table — no duplicates): the thumbbar owns
  PAGE-level actions (top/copy/theme) + SERVER-side narrowing (a filter
  that fires a new query). The table owns ALL client refine: sort,
  filters, page/size, density, cards, views, compute, insights. Category
  buttons are not a separate bar — low-cardinality text columns sprout
  preset chips automatically. Two controls doing the same job = bug.
- Multi-table filtering (one filter driving several tables) is NOT decided
  here — open question, see below.

## U4. Views, presets, share links

Two different things, both called "views" — the library supports both:

- **Data views (server):** named queries across sources
  (`funding = dex1 UNION dex2`). Defined once in backend config, addressed
  by name in `/api/rows?view=<name>`. This is how multi-source looks like
  one table. See `e068-tablelib`.
- **Display views (client):** a named snapshot of GUI state — filters,
  sort, page size, density, cards, visible columns. Users save them, pin
  them as chips on the page, and share them as links.

Rules for display views:
- Every table state serializes to the URL hash
  (`#tl-<ns>=<base64-json>`). Opening the link reproduces the exact view —
  no account, no server. A Share button copies that link (1 tap).
- Experiments ship **presets** (curated views, e.g. "cheap only"): chips
  above the table, defined in one config list, not in code.
- Users save their own views (name + state, `localStorage`), pinned as
  chips next to presets. Missing views/share = WARN `NO_SAVED_VIEWS`.
- Chrome budget: max 3 preset chips + 3 insight chips visible, rest behind
  `+N more` (ranked: fewest outliers first, strongest correlation first).
  Unbudgeted chips = WARN `CHIP_SPAM`. Outlier views only when selective
  (1–8 outliers); derived columns never correlate with their sources
  (lineage map). Embedded total must equal embedded rows or say `N of M`
  (FAIL `COUNT_MISMATCH`).

## U5. One-tap analytics, generic presets, AI suggestions

Presets are data-driven (derived from the table's own columns/rows via
`stats.auto_presets`), never hard-coded per experiment: lowest-N per
numeric column, outlier views, and the same for every table.

Every numeric column is one tap away from its stats (min/max/mean/median/
stdev), every pair from its correlation, every row from outlier flags
(z-score) and from row-vs-transform compares. Users add computed columns
(A/B, A−B, A+B, A% of B) from a picker — no formulas typed, no statistics
knowledge needed.

Charts are cell renderers, not pages: `spark` (unicode trend), `poly`
(SVG polygon), `bar` (proportional bar) — same renderer server and client.

AI integration is a shape, not a vendor: heuristics (`stats.suggest`)
and any model return identical suggestions
`{title, detail, state}` where `state` is a display-view state — so every
insight is one tap from its view, and the GUI cannot tell heuristic from
AI. Optional endpoint: `POST api/suggest {cols, rows[:200]}` →
`{suggestions: [...]}`. Offline heuristics always work; the endpoint only
upgrades them.

## Open question (not a rule yet)

How should one filter drive several tables on a phone without confusion?
Candidates: a global filter row above all tables with per-table opt-out, or
per-table filters with a "copy to all" tap. No decision — proposals welcome,
no implementation until decided.

## How to adopt

Same one line as TABLE_FIRST.md — both files live in `e000-fundamentals/`:

```markdown
## Inherits
- [../../e000-fundamentals/TABLE_FIRST.md](../../e000-fundamentals/TABLE_FIRST.md) — table-first rule
- [../../e000-fundamentals/TABLE_UX.md](../../e000-fundamentals/TABLE_UX.md) — table UX rules
```

```bash
python3 ../e000-fundamentals/bin/table_check.py <experiment>
# Tier 1 FAILs block. Tier 2 WARNs list the UX gaps to fix next.
```

Implementation: [e068-tablelib/](../e068-tablelib/AGENTS.md) — every rule
above ships there once, tested by `tests/test_lib.sh` (Tier 1 PASS + 0 WARNs).
