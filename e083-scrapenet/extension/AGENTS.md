# extension/ — ScrapeNet Collector (vanilla MV3, zero deps)

## Per-site support matrix (tested with a driven real browser)

| Site | Adapter | Status | Date | Proof |
|---|---|---|---|---|
| en.wikipedia.org article | generic-article | works (no login) | 2026-09-29 | 1 row: title + body>200 chars (author/published empty — Wikipedia ships no meta author) |
| books.toscrape.com product | generic-product | works (no login) | 2026-09-29 | 1 row: name + £51.77 via DOM fallback (site has no JSON-LD; basket form removed from markup) |
| demo.vercel.store product | generic-product | works (no login) | 2026-09-29 | 1 row: name + lowPrice 15.0 + USD + image via JSON-LD AggregateOffer |
| news.ycombinator.com front | suggest → server ops | works (no login) | 2026-09-29 | no adapter matched → suggest proposed `td.title` (conf 0.6) → approved → 31 clean rows ingested |
| x.com / twitter.com | x-timeline | needs-login | 2026-09-29 | /home redirects to login wall; adapter correctly returns null; parse proven on tweet-markup fixture |
| google.* /search | google-search | blocked | 2026-09-29 | IP-level "unusual traffic" sorry on stock CDP Chrome, uc headless AND uc headful; curl gets JS-shell only. Parse proven on realistic fixture |

## How to add an adapter in <30 lines

Copy `adapters/x.js`. You need exactly five things:

1. `id`, `name`, `dataset` (e.g. `my-forum`, `My Forum`, `forum-posts`).
2. `host_pattern` — regex tested against the hostname (e.g. `(^|\\.)example\\.com$`, or `"."` for generic).
3. `detect(url, doc)` — cheap boolean using `doc.querySelector` only.
4. `extract(doc, url)` — returns `{ rows, raw_extra? }`; touch the DOM only via `querySelector(All)` / `getAttribute` / `textContent` so the node unit test can run it.
5. `recipe` — one-click binding the popup creates: `{ id, name, dataset, match, description, schema, fn, where }`. `fn` maps `raw.rows || raw.cards` → records.

Register specific sites before generics (load order in `manifest.json` =
match priority: x → google → product → article). Then add fixtures to
`test/adapters_test.js` and run `node test/adapters_test.js`.

## Transform-location tradeoff (`where`: client | server | both)

- **client** (default, private): `recipe.fn` runs in the content script; the raw page never leaves the browser. Use for anything personal or login-walled.
- **server** (`POST /api/transform`): raw (+ stripped 100KB snapshot when a `css-select` op needs it) is sent to the collector, which runs ONLY the declarative op set (`css-select`, `json-path`, `regex`, `map`, `filter` — anything else rejected by `validate_ops()`; the server never evals JS). Use for suggested recipes and heavy pages; less private by design.
- **both**: runs client fn AND server ops, merge-dedupes by JSON. Use when either side may miss rows; costs one extra round-trip.

Suggested (visit-time) recipes are always created with `where: server` + the
approved ops, so capture works with zero client code.
