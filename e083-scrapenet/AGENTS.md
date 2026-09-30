# e083 — ScrapeNet (the users are the scraping network)

Browser extension nodes intercept page/API data on user-enabled hosts,
transform it with recipes, and send it to a collector that publishes
datasets as public APIs and pays nodes in crypto. Rule-based AI refines
transforms and suggests how to monetize each dataset.

## Product

| Surface | User action |
|---|---|
| Dashboard `/` | ONE page. See live records, edit + test recipe transforms, publish a dataset (get public API URL), check per-node earnings, get 3 business ideas. Signup is self-serve (name → node_id + token); writes need the token, reads stay public. |
| Extension popup | Enable/disable scraping per host, pick transform recipe, set collector URL, trigger Scrape-now (Alt+S). See records captured. |
| Extension options | Set node id, payout wallet address, collector URL, API-publish consent toggle. |
| Public API `/api/public/<dataset>` | Anyone fetches the published dataset JSON (this is the product being sold). |
| Install `GET /download/extension.zip` | Server zips `extension/` on the fly — the stranger install path. |
| Signup `POST /api/signup` | `{name, referral_code?}` → `{node_id, token, referral_code}`. Token shown once, stored hashed 0600. |
| Dataset page `GET /dataset/<id>` | Human share page: stats, sample rows, copy-API-link, `?ref=` attribution. |
| Leaderboard `GET /api/leaderboard` | Referrers ranked by invited signups + their records + referral earnings. |

Rule: scraping is opt-in per host — content script does nothing unless the
user enables the host in the popup.

## Architecture

```
extension/          Manifest V3, vanilla JS, zero deps
  manifest.json     content_scripts (all urls) + popup + options
  background.js     service worker: relays captures -> POST collector /api/ingest
  content.js        hooks fetch/XHR (intercept proof), captures raw (JSON-LD,
                    product cards), applies recipe fn string, sends records
  popup.html/js     per-host enable, recipe pick, collector URL, scrape now
  options.html      node id, wallet, collector URL, publish toggle
server/app.py       stdlib only: static public/ + /api/*
  /api/health       alive + counts
  /api/ingest       POST records from extension (node_id, dataset, records[])
  /api/records      list/filter (dataset, node_id, limit)
  /api/recipes      CRUD transform recipes (GET/POST/PUT?id=/DELETE?id=)
  /api/refine       rule-based refiner: dedupe, schema inference,
                    field-quality score, selector-fix suggestions (+LLM slot)
  /api/publish      POST {dataset} -> snapshot to data/published/<id>.json
  /api/events       POST telemetry {v:1, session, ts, page, event, detail?, ms?}
                      (page_view, click:<id>, download, signup, first_proof_seen,
                      js_error, idle_45s; random session id, no IPs)
  /api/funnel       funnel {views, downloads, signups, publishes, stuck_sessions[{session,short,synthetic,last_event,last_detail,last_at}], bots_hidden, bots_total, verdict{level,line}} (?bots=1 reveals bots; bots = check-*, *-probe/CI UAs, tagged synthetic at ingest; thresholds in needs.json funnel_*)
  /api/generate     POST {html?, url?, name?, dataset?} -> rule-based recipe
                      proposal from pasted HTML or fetched URL (+LLM slot)
  /api/last-capture newest row: raw capture -> transformed record (+recipe fn)
  /api/last-payout  newest node's math: records x rate - commission = payout
Recipes carry `where` (client|server|both): CLIENT transforms in the browser
(raw never leaves), SERVER sends raw for AI refine, BOTH tries client first.
  /api/public/<id>  published dataset as public JSON (the monetizable API)
  /api/earnings     per-node ledger: records x payout - commission = net
  /api/ideas        rule-based monetization suggester (3 ideas per dataset)
public/index.html   single-file dashboard, mobile-first, 15s refresh, zero deps
needs.json          ALL machine values (port, bind, token, commission, paths,
                    llm_model_endpoint slot). No hardcoded IPs/ports/URLs.
data/recipes.json   3 shipped recipes: product-price, job-listing, crypto-price
data/records.jsonl  append-only captures (seeded with 4 demo rows)
data/ledger.jsonl   node payout addresses (seeded demo nodes)
data/published/     published dataset snapshots
bin/serve.sh        start/stop + live URL report (LAN/tailnet resolved live)
test/check.sh       ingest->records->publish->earnings->ideas->refine smoke
```

## Transform pipeline

raw capture (adapter `rows` or legacy DOM/API `cards`)
→ recipe transform, placed by `where` (client|server|both, default client)
→ normalized record → POST /api/ingest → published API.

Adapters: `extension/adapters/` registry (`{host_pattern, name, detect(),
 extract(), recipe}`) — x timeline, Google search, generic article,
generic product. Popup suggests on visit: match → one-click extract;
no match → stripped snapshot (100KB, no inputs) → `POST /api/recipes/suggest`
→ user approves the proposed field mapping with one click.

Server op set (SAFE subset for `where=server|both`, executed by
`POST /api/transform`; `validate_ops()` rejects anything else — the server
never evals recipe JS):

- `css-select {selector, fields:{out:{sel,attr}}, limit}` — small CSS subset
  (tag/.class/#id/[attr]/:nth-child/descendant/comma) over `raw.html`.
- `json-path {path}` — dotted path with `[*]`/`[N]` over the raw object.
- `regex {field, pattern, group, out}` — per-row string extraction.
- `map {fields, drop, const}` — rename/drop/add-constant per row.
- `filter {field, exists|equals|contains|gt|lt}` — keep matching rows.

Tradeoff: client = private (raw never leaves the browser); server = smarter
(shared ops, AI-refinable) but raw travels to the collector; both = run both,
merge-dedupe. Recipes carry `ops[]` alongside the legacy `fn`.

## AI slots (rule-based today, LLM plugs in via needs.json)

- `/api/refine`: dedupe + schema inference + quality score + selector-fix
  suggestions. If `llm_model_endpoint` is set, the response also returns
  `llm_available:true` + a ready-made `llm_prompt` (recipe fn + failing
  sample) for the caller to send to the model.
- `/api/ideas`: keyword rules on dataset schema (price/job/crypto/title/
  symbol). An LLM can replace/augment `suggest_ideas()`; the endpoint shape
  stays the same.

## Run

```bash
bash bin/serve.sh            # start + URL report
bash test/check.sh           # must print PASS
```

## Adapter support matrix (live-tested 2026-09-29, see ADAPTERS-E083-REPORT.md)

| Site | Adapter | Status | Date | Evidence |
|---|---|---|---|---|
| x.com home / explore | x-timeline | needs-login (login wall, adapter correctly silent, 0 rows) | 2026-09-29 | onboarding redirect URL + null detect |
| x.com logged-out profile | x-timeline | needs-login (bio loads, 0 `article[data-testid=tweet]` even after scroll) | 2026-09-29 | 0 tweet nodes, null detect |
| google.com search | google-search | blocked (sorry/index wall headless AND headed; curl = JS shell) | 2026-09-29 | wall URL; extract() proven in-browser on realistic markup, 2 rows |
| en.wikipedia.org article | generic-article | works | 2026-09-29 | 1 row: title + 8000-char body |
| books.toscrape.com product | generic-product | works (DOM fallback, no JSON-LD) | 2026-09-29 | 1 row: name + £51.77 |
| demo.vercel.store product | generic-product | works (JSON-LD AggregateOffer) | 2026-09-29 | 1 row: name + 15.0 USD + image |

## How to add an adapter in <30 lines

Copy `extension/adapters/x.js`, change the id, `host_pattern` regex,
`detect(url, doc)` (return true only on a real signal, never on login walls)
and `extract(doc, url)` (return `{rows: rows.slice(0, 50)}`, cap text fields).
Add the `recipe` binding (`id`, `dataset`, `schema`, pure-mapping `fn`,
`where: "client"`). Register order = match priority (specific first, generics
last). `registry.js` validates the shape and throws on duplicates. Add a fixture
case to `test/adapters_test.js`, run it + `bash test/check.sh`, and log one live
browser capture in ADAPTERS-E083-REPORT.md. No new permissions or deps.

## Extension load test (cannot be opened headless)

1. Open `chrome://extensions`, enable Developer mode, Load unpacked → `extension/`.
2. Open extension Options: set collector URL to the `bin/serve.sh` URL, node id, wallet.
3. Visit any shop page, open popup, enable host, pick `product-price`, Scrape now.
4. Dashboard `/` shows the new record under Live records; earnings board credits the node.

`test/check.sh` validates `extension/manifest.json` parses as JSON.

## DONE ladder

1. WORKING — :8383 serves dashboard + API, ingest→records→publish→earnings→ideas→refine, check.sh PASS.
2. DEPLOYED — tailnet URL reachable, serve.sh running, extension load-tested on a live shop page.
3. TESTED — 3 recipes capture real rows on 3 host kinds; refine suggests a real selector fix.
4. ANNOUNCED — owner ping with dashboard + one public dataset URL.
5. MONETIZED — first external API consumer or dataset sale; commission math verified against ledger.

## Strategy context
Shared Q&A covering this experiment + its sibling: `../QA-E082-E083-DEX-TRADING.md` (new ideas, improvements, DEX maker/taker connections, bear-market businesses).
