# tablelib README (v0.2.0)

One server-side renderer + one client for every p4 table. You pass **rows +
columns**, it returns HTML that passes `table_check.py` by construction:
real `<tr>` rows, counter, pager, sortable headers, per-column filters,
density + cards, saved views + share links.

## 30-second quickstart

```python
import sys
sys.path.insert(0, "../e068-tablelib")
from tablelib.render import render_table

COLUMNS = [
    {"key": "symbol", "label": "token", "kind": "text", "ph": "token"},
    {"key": "mcap_usd", "label": "mcap $", "kind": "num", "fmt": "{:.3g}"},
    {"key": "share", "label": "share %", "kind": "bar", "fmt": "{:.2f}"},
    {"key": "trend", "label": "6wk", "kind": "spark"},
    {"key": "through", "label": "through", "kind": "date"},
]
html = render_table(rows, COLUMNS, total=len(rows), page=1, per=10,
                    sort_key="mcap_usd", sort_dir=-1, ns="mytable")
```

```html
<link rel="stylesheet" href="tablelib/table.css">
<script src="tablelib/table.js"></script>
<script>document.addEventListener('DOMContentLoaded', function(){ tlRender('mytable'); });</script>
```

```bash
python3 ../e000-fundamentals/bin/table_check.py <your-experiment> --served <page.html>
```

## Column kinds

| kind | cell value | renders | notes |
|---|---|---|---|
| `text` | str | escaped text | auto-detected as date if ≥80% of values parse (see dates) |
| `num` | number | formatted (`fmt`, e.g. `{:+.1f}`) | sortable, min/max filter |
| `bar` | number | mini bar + number | scale = column min..max unless `scales={key:(lo,hi)}` |
| `pill` | number | number + badge from `pill_key` row field | badge uses `.tl-thin` (contrast-safe both themes) |
| `spark` | list[numbers] | ▁▂▃▄▅▆▇ unicode trend | SSR + client identical |
| `poly` | list[numbers] | inline SVG polygon | same |
| `date` | epoch s/ms, ISO-8601, `MM/DD[/YYYY] [HH:MM]` | `MM/DD HH:MM` UTC + `data-ts` | range filter, chronological sort |
| `link` | `https://…` URL string | short-text external link (`target=_blank`, `rel=noopener`) | label via `link_text` (default ↗); never sorted/filtered; non-`http(s)` renders as — (XSS-safe) |

`cls` = your host-page class for simple/full hiding (lib never hides for you).
Give secondary columns e.g. `cls: "c-hid"` and add one page rule —
`body.simple th.c-hid, body.simple td.c-hid, body.simple .tl-f.c-hid { display: none; }` — and the
Simple/Full buttons actually do something in table and cards views alike. Start `<body class="simple">`
unless your table is narrow.
`ph` = filter placeholder (`None` still gets a filter; `nofilter: True` opts out —
ragged filters trigger a WARN, so opt out deliberately).
`pill_key` required for `pill`.

## The 5 params you need (rest are advanced)

`render_table(rows, columns, total, page=1, per=10, sort_key=None, sort_dir=1, ns="t")`.
`total` vs `len(rows)`: when equal the pager says `N rows`, else `N of M rows`
(`COUNT_MISMATCH` FAIL if you lie). `ns` = per-table localStorage namespace.

Advanced (defaults sane, read before using):
`filters`, `density`, `presets` (curated view chips), `suggestions`
(`stats.suggest` shape), `share` (save/share buttons),
`insights=True` / `compute=True` (set False to drop those blocks;
the views block is also dropped when `presets=[]` and `share=False`),
`scales`,
`card_layout` (default: title+headline then pairs), `bare` (table+data only,
no controls — you lose Tier-2 compliance, pager included),
`derived` (`{col: source_col}` lineage map so suggestions skip trivial
self-correlations), `row_click` (**JS function name only**,
`[A-Za-z_][A-Za-z0-9_]*`, plus `row_click_key` row field).

## Dates (explicit is better than magic)

Prefer `kind: "date"` with epoch seconds. The multilingual relative parser
(`3h ago`, `hace 3 horas`, `ayer/hoy`) exists in **both** `render.py` and
`table.js` — they must stay in sync manually (known wart, see below).
Text columns that look ≥80% like dates are auto-treated as dates
(display unchanged). Strings packing 2+ dates are never parsed: split them
into atomic columns (TABLE_FIRST rule).

## Vendoring + versions

No package manager: experiments copy `tablelib/table.css` + `tablelib/table.js`
into their `output/` at refresh time and stamp `version.json`.
Check `VERSION` here after pulling — `0.2.0` = XSS escaping + row_click
sanitize + generic suggest labels + side-by-side min/max CSS.
Paste `render.py` nowhere; import it.

## Security notes (CSP + XSS)

- All Python cells are HTML-escaped; all JS text paths are escaped since
  0.2.0 (`tlEsc`). If you bypass `tlCell` with custom HTML, you own the escaping.
- Headers use inline `onclick="tlSort(...)"` (like all controls). A strict
  `script-src` CSP will block them — that is a known wart, not a feature.
  `row_click` accepts a bare function name only for the same reason.
- State lives in `localStorage` (`tl-<ns>`, `tl-uviews-<ns>`, `tl-density`,
  `tl-cards`) + URL hash (`#tl-<ns>=<base64>`). No cookies, no server.

## Known warts (honest list, fixes welcome HERE not in experiments)

1. 17-param `render_table` — needs a builder/defaults pass.
2. Date parser duplicated py/js by hand; e059 once shipped a client shim
   because date support landed mid-flight. Needs one grammar + generated tests.
3. Global `tl*` functions + inline handlers (CSP-hostile). Needs namespaced
   module + event delegation.
4. All rows embedded as JSON (`#tl-data-<ns>`) — fine under ~500 rows,
   heavy beyond. No server-pagination story yet.
5. Host page owns `.c-*` simple/full rules — easy to forget (wide table on
   phones). A default hiding heuristic would help.
6. `stats.suggest` heuristics are thin (outliers + |r|≥0.7); `POST api/suggest`
   contract is documented but no server ships with the lib.
