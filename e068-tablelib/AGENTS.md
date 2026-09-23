# e068 — Tablelib: shared table library for all p4 experiments

One renderer, every table. Tables comply with
[../e000-fundamentals/TABLE_FIRST.md](../e000-fundamentals/TABLE_FIRST.md) and
[../e000-fundamentals/TABLE_UX.md](../e000-fundamentals/TABLE_UX.md)
**by construction** — experiments pass data, never hand-roll HTML.

## Layout

- `tablelib/render.py` — server-side render: controls + sortable/filterable
  thead + rows with `data-l` + pager with per-page select. Embeds the column
  spec + rows as JSON for the client.
- `tablelib/table.js` — client interactivity, zero config: tap header = sort,
  per-column filters, page size, simple/full density, cards (vertical) view.
  State persists per table in `localStorage`.
- `tablelib/table.css` — contrast-safe pills (both themes), sticky header,
  filter inputs, cards layout. Namespace `tl-`; never restyle host pages.
- `example/` — sample dataset + `build.py` producing a demo page.
- `tests/test_lib.sh` — the library's automated test: builds the demo and
  runs `table_check.py`. Tier 1 must PASS, Tier 2 must print zero WARNs.

## Using it (one import, no thinking)

```python
from tablelib.render import render_table
html = render_table(rows, COLUMNS, total=len(rows), page=1, per=10, ns="m")
```

```html
<link rel="stylesheet" href="tablelib/table.css">
<script src="tablelib/table.js"></script>
```

Then run the verifier — it is this library's test suite and your page gate:

```bash
python3 ../e000-fundamentals/bin/table_check.py <your-experiment> --served <page.html>
```

## Analytics (stats.py) + charts + AI hook

- `tablelib/stats.py` — describe/corr/outliers/auto_presets/suggest.
  Suggestions are `{title, detail, state}`; `state` is a display-view
  state, so each insight chip opens its view in one tap.
- Cell charts: `spark`, `poly`, `bar` kinds (SSR + client identical).
- `+ column` picker: A/B, A−B, A+B, A% of B between any numeric columns.
- AI contract (optional): `POST api/suggest {cols, rows[:200]}` →
  `{suggestions: [...]}`. Heuristics work offline; a model only upgrades
  them. GUI treats both identically.

## Clients

- e059-crypto-valuations — first client, migrated (SSR + client via tablelib; domain UI kept: verdict/alerts/cats/thumbbar/copy/dark).
- e058-funding-scanner — second client, migrated (FastAPI SSR per request: coins/paper/signals; dump-all removed; pickCoin row-click kept).
- e058-funding-scanner — second (port 8320, column-layout fix).

## Rule for contributors

New table feature? It lands HERE with its Tier 2 check in `table_check.py`,
not copy-pasted into an experiment. One implementation, all tables inherit it.

## Docs

Start with [README.md](README.md) (quickstart, kinds, params, vendoring,
security, known warts) — not the `render.py` docstring. Version in [VERSION](VERSION).
