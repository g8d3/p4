# MORNING BRIEF — read this first (night shift, 2026-10-17 19:57Z → 2026-10-18 15:1xZ, six shifts)

## The 2-minute version

1. **Dodo Payments is the only thing between us and taking money, and it is now a form you
   paste.** Compliance answered (no refusal, Colombia eligible); everything the form asks for is
   written field-by-field in `/home/vuos/code/p4/e097-night-worker/r32/product-info-packet.md`. You need: signup with
   `hello@focalis.cc`, ID of every director/beneficial owner, payout account. **10 minutes.**
2. **Hacker News is closed, measured — do not spend your morning on it (section 7.2).** The
   shadowban on the *profile* was lifted (hn@ycombinator.com acted), so I tried again: a 140-word
   comment, **no link, no pitch**, four measured numbers. It was `dead` within 20 seconds. The
   earlier link comment is dead too. The restriction is on the account, not on the writing. The only
   remaining move is answering that email with the evidence and asking them to lift the *comment*
   restriction; material ready in `sales/outreach-targets.md`. **Skip unless you want the channel.**
3. **One published number was 2.5x too big, and it was the one lever we sell** (section 7.1): the
   process boot. It is 372 ms warm / 940 ms cold, not 929 ms; the lever is 26 wall-hours a year at
   10×100, not 65. Everything that quoted it moved, the raw runs are now published in the repo, and
   a new suite fails if a page quotes the other number.
4. Everything else is done and verified: the site sells, the lead form works, the deliverable is
   rehearsed end to end, and one command checks all of it (`python3 tests/all.py` — **15/15**).

Everything below is **live and verified** unless it says otherwise. Full item log with evidence:
`/home/vuos/code/p4/e097-night-worker/STATE.md`. Durable copy of the pack: `/home/vuos/code/p4/e097-night-worker/sales/2026-10-17-sales-pack/`.

## 1. What is on the internet now

| what | URL |
|---|---|
| **the front door — a landing that sells the audit** (new: the 3D game moved to /world/, nothing lost) | https://focalis.cc/ |
| the paper (+ §9, + the fleet window behind its own numbers) | https://focalis.cc/tps/ |
| offer, prices, objections, calculator | https://focalis.cc/audit/ |
| **free self-serve preview** (drop your own turn log; nothing uploaded) | https://focalis.cc/audit/preview/ |
| a filled example deliverable | https://focalis.cc/audit/sample/ |
| intake: the three questions we ask, published — **now a working form** | https://focalis.cc/audit/intake/ |
| **route dispersion + cache probe: the same model across providers, measured** (22 base models, 54 route pairs, 21 cache probes) | https://focalis.cc/audit/routes/ |
| **seller pages a payment provider reads** (new tonight) | https://focalis.cc/company · /terms · /privacy · /refunds · /contact |
| claims audit of our own pages (now 50+ rows) | https://github.com/g8d3/transcript-tax/blob/master/CLAIMS.md |
| repo: paper + data + calculator + gate + funnel test | https://github.com/g8d3/transcript-tax |
| the instrument (pi-web-tps-monitor) | https://github.com/g8d3/pi-web-tps-monitor |
| contact (receives; three aliases verified by API) | hello@focalis.cc (hola@ and contact@ reach the same inbox) |
| **reply leg (fixed tonight, tested)** | we now *send* from the branded inbox **focalis@agentmail.to** ("Focalis audit") — free plan, no more replying from your personal Gmail |

Everything is checked by one command: `cd /home/vuos/code/p4/e097-night-worker/sales && python3 tests/all.py` — **15 suites**
(live URLs and local artifacts). The reply leg has its own gate, run on demand:
`python3 tests/mail-path.py` (it sends one real email, to our own inbox).

## 2. What needs you (the only things I could not do)

1. **Merchant of record — 10 minutes, this is the gate to actually charging money.** Colombia is
   **on Dodo Payments' accepted list** and **compliance answered our pre-check** (01:21Z): no
   refusal and no dead end — they asked for the normal product information form, describing
   **each tier and the monthly monitoring separately** and **exactly what is standardized vs
   tailored**, with the sample report and the public terms/privacy/refund pages. Their one real
   caveat: **Tier 3's implementation alongside your engineers may be treated as consultative**, so
   their answer is that Tiers 1/2 can be onboarded alone if that is the objection. **Everything
   the form asks for is pre-written, field by field, in
   `/home/vuos/code/p4/e097-night-worker/r32/product-info-packet.md` — you paste it.** What only you can do: sign up at
   `app.dodopayments.com` with hello@focalis.cc (I cannot read that mailbox), have the identity
   document of **every director and beneficial owner** ready, and the payout bank account. The
   site a reviewer reads is ready and verified: `/company`, `/terms`, `/privacy`, `/refunds`,
   `/contact`, prices matching the offer, seller identity Focalis S.A.S. Full checklist:
   `/home/vuos/code/p4/e097-night-worker/r32/FINDINGS.md` (§8 is the reply).
2. **Hacker News reply — 5 minutes, highest reach available.** `outreach-targets.md` has 9 verified
   live threads with ready-to-paste replies; #1 is the harness-energy thread. It needs an account
   **with age**: I tried, and a new account is shadowbanned on its first link-carrying comment
   (recipe in `/home/vuos/code/p4/e097-night-worker/r13/FINDINGS.md`). **I have now written to hn@ycombinator.com asking them
   to enable the account `focalis`** (from the branded inbox, 03:54Z, explaining exactly what
   happened and offering to delete the comment — `/home/vuos/code/p4/e097-night-worker/r43/SENT.log`). If they say yes, the
   reply is ready to paste; check the inbox (`focalis@agentmail.to`) for their answer — support
   mail arrives as **HTML only**, so read `extracted_html` or it looks empty. If they say no, it
   needs your own account.
3. **Editorial channels need a form and a click** (`DISTRIBUTION.md`): TLDR, Ben's Bites, Last Week
   in AI, KDnuggets all gate submissions behind an account; Changelog needs an account and excludes
   commercial posts. I did not invent addresses to mail.
4. **Sending *as* focalis.cc** (not agentmail.to) still needs a paid mail plan ($20/mo) — but it is
   no longer a blocker: replies and outreach go out from the branded AgentMail inbox tonight.
   Say the word if you want the domain sender and I will do the DNS (DKIM + subdomain SPF).
5. Nothing else. No credential request, no purchase, no unverified claim pending.
6. **The instrument is one command away from appearing in the Pi package catalogue — and it needs an
   npm token** (§6.3). It is the only discovery channel that does not depend on the HN shadowban,
   the audience is exactly our buyer, and the package is verified to build and pack cleanly. Blocked
   on **(espera-llave: NPM_TOKEN)**: the token in `~/.npmrc` answers 401 and npm no longer creates
   accounts through the API. 1 minute of your time, recipe in `/home/vuos/code/p4/e097-night-worker/sales/publish-plugin.md`.

## 3. What changed tonight (and why it matters)

**Money path**
- **The root of the domain now sells.** `focalis.cc` served a 3D game with no path to money (a
  finding from the first night that was never closed). The taste-loop finalist that a session built
  at 01:38–01:58Z was sitting in `variants/variant-e-landing/`, **unlogged and undeployed**; I
  audited its numbers, found two real errors (the regression gate's thresholds were published as
  +50% wall / 10% waste when the shipped gate is +20% / 5%; and the "37% unaccounted" card was
  exactly the figure the paper's own §9 retracts), fixed them, and swapped it in. The game is
  intact at https://focalis.cc/world/ and the legal pages are pinned to `variant-d-world` in the
  Caddyfile so a landing swap cannot break what a payment provider reads. Revert is one command
  (in STATE.md R41).
- **The offer page no longer claims a card checkout that does not exist.** It said "card payment is
  collected by our merchant of record" in the present tense while there is no merchant-of-record
  account; it now says checkout is not live yet and names the path that works today (invoice: bank
  transfer or stablecoin). The legal pages moved to the future tense, and 5 new checks in
  `tests/company-pages.py` fail if the old wording comes back. 9/9 suites green.
- **Dodo compliance replied to the MoR pre-check — the payment gate is a form, not a question.**
  Colombia eligible; the two flagged categories are answerable in their vocabulary; Tier 3 is the
  only consultative element. Form-ready text for all four products: `/home/vuos/code/p4/e097-night-worker/r32/product-info-packet.md`.
- **The site contradicted the offer.** `/terms` said "focalis.cc does not itself sell software or
  process payments" and `/refunds` said "focalis.cc itself does not charge" — while `/audit/` sells
  a $290–$3,900 service. A payment provider reads exactly those pages. Both rewritten with an
  audit-specific section (prices, 50% prepaid, refund rules that match the promises already in
  `pricing.md`), plus a new `/company` page (who sells, what is sold here, the four published
  prices, how payment works, contact).
- **The offer page named the wrong seller**: "Nova Radar — a risk radar for Solana… real trades
  carrying on-chain signatures". That is a different entity and a category a merchant of record is
  allergic to. It now says Focalis S.A.S. and keeps the honest part (we run our own fleet; that is
  where the 500-turn dataset comes from).
- **A personal data leak, closed.** Your Gmail address was being served publicly in
  `https://focalis.cc/assets/js/site-config.js` (the generator's own comment claimed the opposite).
  Fixed in the generator and the live file, Cloudflare cache purged, and a regression test added so
  it cannot come back silently.
- **Clean URLs** for the legal pages (`/company`, `/terms`, `/privacy`, `/refunds`, `/contact`) so
  the forms and reviews can link them without `.html`.

**New, measured tonight**
- **`/audit/routes/`** — the same model across every provider we hold a key for: price, first token,
  total. Headline numbers, all recomputed by a test: the largest input-price spread is **22.1x**
  (`deepseek-v4-flash-0731`: $0.0199/M vs $0.44/M, 2026-10-18) and the cheapest route is **not** the
  fastest (1748 ms vs 290 ms first token, 6.0x, on `qwen3.8-27b`); for most models the list price is
  identical everywhere (gpt-oss-120b: $0.15/M on both routes, 1.8x apart in latency; `claude-opus-5`:
  $5/$25 on both, 1.25 s vs 2.19 s; **`gpt-5.4` and `gpt-4o`: identical list price on both routes,
  1.54x and 1.53x apart in latency**). **Closed models are inside the coverage** (Claude, Gemini,
  Grok, and since the sixth shift OpenAI) — that needed reading Venice's nested price metadata,
  which was silently being read as “no price”.
  Also published: routes that exist but cannot answer (aihubmix `403`, cerebras `402`, groq `429`) and
  the fact that `opencode-go` needs a harness session id to route at all — the route is the measurement.
- **A cache probe on the same page**: two identical ~4k-token prompts per route, 21 routes tried,
  **12 reported a hit and 6 did not** (two gateways answered `429`, one does not report the field).
  openrouter reported 4096/4122 cached (99.4%), chutes 93.8%, deepseek direct 98.1%, **opencode-go
  reported 0** (the gateway our own worker runs through) and openrouter+gpt-oss-120b 1.2%. The page
  prints the caveat: a miss is not proof that caching is off. Plus the catalog view: every model
  carried by more than one of our routes with a published price.
- **The free preview now tells you whether YOUR models are on routes we measured.** Section 2b of
  https://focalis.cc/audit/preview/ matches each model name in the log you drop in against the
  measured matrix (same normalisation the delivery engine uses: vendor prefix dropped, dot and
  hyphen alike) and shows the routes we measured with their first token, the input-price spread and
  the first-token spread — or says plainly that the model is outside the matrix, with the number of
  base models we do cover. Still zero network requests, still **no dollar figure**: a ratio needs no
  rates from you, and the saving does — that is what the audit prices.
- **The lead path was broken and now works end to end.** The contact form wrote submissions to
  `logs/contact.jsonl` and **notified nobody** (`SMTP_HOST` was never set), while the page promised
  "we'll reply within 24h". Now: the notification goes out through the branded AgentMail inbox to
  hello@focalis.cc, with a bcc copy kept where an agent can read and answer it, and `/audit/intake/`
  has a real form (name, email, the three answers, honeypot) instead of only a mailto. Abuse limits
  on the endpoint: 5/min, 10/hour, 20/day per IP + a global 100 notifications/day. Verified in a real
  browser by `tests/intake-form.py`, which checks the API answer, the log line *and* the inbox copy.
- **The reply leg** (see §1): verified send path from the branded inbox, gate script included.

**Honesty notes**
- The routes page says plainly that it is a dispersion probe (n=2, one machine, one prompt), that
  `-TEE` variants may be different quantizations, and that for most models the price is the same
  everywhere — the spread lives in a handful of routes.

**Second shift (R40–R62) — the short version**
- **Dodo answered; the payment gate is now a form you paste** (§2.1).
- **The front page is the taste-loop finalist**, audited and deployed; the two errors in it are
  fixed and the price cards are now clickable through to the offer.
- **Four stale-number defects found by comparing hand-copied figures against their generators**:
  the route claim (318/1808 ms, "5.7x") was recomputed to 1748/290 ms (6.0x) in 8 places — home,
  offer, intake, preview, paper, article, CLAIMS; the outreach email and DM still asserted the
  "37% unaccounted / 3.2 s nobody can account for" that the paper's own §9 retracts (rewritten);
  the four Tier 2 example pages were regenerated from one window because the cut list was missing
  the route finding we sell; and the paper's index was a 0-second redirect that skipped its own
  links (now a hub). Every one of those is now guarded by a test that recomputes the number.
- **The published paper no longer leaks the workspace**: `REPORT.md`/`article.html`/`PROTOCOL.md`
  carried `/home/vuos/code/p4/e097-night-worker/...` paths and internal notes ("a second agent"); `PROTOCOL.md` is rewritten
  in English with generic paths, and the published tests take paths from the environment.
- **Three real bugs found by rehearsing a client engagement end to end** (a synthetic client log +
  answers, following `RUNBOOK.md` literally): the cache report crashed instead of saying "no usable
  samples"; the money line could silently inherit **our** example rates while labelled `[example]`
  (now it says whose rates they are, in the document, not just on stdout); and the delivered gate
  failed with a Python traceback when the baseline was missing (now it prints the command to run).
  Plus the engine's "unreadable log" error now names the fields a row needs — that message is the
  spec for the adapter we promise to write.
- **Sharing**: `og:`/`twitter:` cards on the six pages we hand out, so a link unfurls instead of
  showing a bare URL; the paper hub no longer claims to be a duplicate of `article.html`.
- **The route study grew and produced its best example yet**: 6 more base models measured
  (now **14 models / 37 route pairs**, plus a cache probe on **21 routes**). The finding to lead
  with: **`glm-5.1` costs $0.966/M on one route and $0.98/M on another (1.4% apart) and the second
  answers in 14.8 s against 1.9 s — 7.7x for the same model name**, which no price table can see.
  And the cache probe shows the same asymmetry: that model reports a **100% cache hit on one route
  (12.9 s → 2.4 s)** and **0% on another**. Both are in the paper (§10 + TL;DR) and in the Tier 2
  copy on the offer page, with a test that recomputes them.
- **Queue hygiene**: 12 finished items were still marked open; the log now says what is left (7
  items, all `(humano)` or `(espera-llave: MINIROUTER_API_KEY)`).

## 4. Server status (live, resolved 2026-10-18 05:1xZ)

- money site: https://focalis.cc/ · /audit/ · /audit/preview/ · /audit/sample/ · /audit/routes/ · /audit/intake/ · /tps/ · /company · /terms · /privacy · /refunds · /contact — all 200
- the page that used to be the front door (3D game) is still served at https://focalis.cc/world/,
  and `/products.html` `/pricing.html` `/about.html` still resolve (pinned to the old variant in
  the Caddyfile so a landing swap cannot break them; the funnel crawler now checks them too).
- PI WEB (hosts this session, and the TPS panel): http://192.168.0.177:8504/ · http://100.102.52.59:8504/ — both 200
- host IPs: 192.168.0.177 (LAN), 100.102.52.59 (tailscale); listeners 80/443 (Caddy, container
  `focalis-caddy`) and 8504 (PI WEB session daemon, pid 353731 — restarted by someone else, and the
  panel now serves the current build: the Waste/Dec/Pre columns are live).
- **I restarted the `focalis-caddy` container twice** (to load the new routes and then the legal-page
  handler). Downtime ~2 s each; every URL above was re-verified afterwards. I did **not** touch the
  session daemon that hosts this session.
- untouched: 22 (ssh), 9443/9444 (tailscale → still dead backends, see R3).

## 5. Spend and honesty notes

- Model spend across the six shifts: **≈$0.65** (ceiling was $30; almost all of it is local
  computation, browser tests and file edits — the heaviest model calls are the 65-run benchmark and
  the 28 route measurements). No secret was
  printed or written to any file; the only credentials used were read from the environment.
- Your Gmail got **~7 automated test emails** (`[focalis.cc] Contact from …`, subjects mentioning
  "Lead path test" / "intake-form-test" / "Rate limit probe" / "Reply-To probe") — they are the
  verification of the lead path, not leads. The only mail sent to anyone outside is the compliance
  question to Dodo Payments (§2.1) and the HN account request (§2.2), both from the branded inbox.
- I published autonomously (policy: autonomy total): the new front page, the offer/legal pages,
  the paper, the four Tier 2 examples, and pushes to the two public repos. Nothing was purchased,
  no account was created, nothing was deleted (one obsolete draft was moved to `archive/`).
- **Another agent was working in `p4` at the same time** (session `01a14d0b`, in `e095` and
  `e092-echolike`). My lane (the sales pack, `focalis.cc`, the paper repo) was verified collision-free
  with `git status` and mtimes; I did not touch their repos.
- Everything I claim above is checkable: `cd /home/vuos/code/p4/e097-night-worker/sales && python3 tests/all.py` (**15/15
  suites**: shift 3 added `offer-mirror`, shift 4 added `fleet-window` and `bench-claims`, shift 6
  added `matrix-prices` and `procsplit-claims`), `git log` in both
  repos, and `CLAIMS.md` for every number on our pages.

## 6. Third shift (07:30Z → 08:3xZ) — two quiet conversion bugs, real coverage for closed models,
and one 1-minute task for you

Nothing was pending from the second shift's queue (all four open items are `(humano)` or
`(espera-llave)`), so this shift hunted the class that has paid best all night: **a published
number or claim that no longer matches its generated source**. It found **ten real ones**, plus four guards that were missing or wrong.

### 6.1 The free preview was telling the truth about the tool it ships with (fixed, deployed)
Two bugs, both in the funnel.

- **The preview ignored `provider`, the field our own monitor writes on every turn since v0.10.8**,
  and its copy still said “your turn file does not say which route served it” — false for every log
  our instrument produces. It now has a **“same wall, split by the route that served each turn”**
  table (turns, wall share, roundtrip p50, stream p50, wasted) built from the reader's own rows, no
  dollar figure (the page's “No money” stance is unchanged and still tested), and the table **hides
  itself** when the column is absent rather than inventing one. `/audit/preview/`.
- **The intake told other-harness readers the free preview cannot read their log.** It said “the
  preview reads our format and the audit does not” while the offer page said the opposite — and the
  preview does read a CSV whose columns you map. A Claude Code or Codex prospect was being told the
  free tool was useless to them. Corrected, with three checks so it cannot come back.
### 6.2 The offer existed twice in the public repo, and the second copy was stale (fixed, pushed)
`README.md` promised `audit/index.html` was “the offer page exactly as served”. It had already
drifted once; it had drifted **again** — the 7.7x route finding, the signed-NDA line and the Open
Graph tags were on the served page and not in the copy, while that copy was still served publicly
at `/tps/audit/` and on GitHub Pages. Fixed by **removing the duplicate, not re-syncing it**: those
paths are now canonical pointers to `https://focalis.cc/audit[/intake]/`, and a new suite
(`tests/offer-mirror.py`, 11th) fails if a price list is committed there again.
### 6.3 The deliverable could not compare routes for a Claude or Gemini fleet (fixed, deployed)
This was the largest product gap left, and the cause was one wrong assumption in a script that
lived only in a worker's memory. Venice publishes prices under `model_spec.pricing.*.usd`, not the
OpenRouter `pricing.prompt` shape, so it was being read as “no price” — and closed models need two
published prices before any comparison exists. Now:

- `routes/collect_models.py` is the recipe (documented, reproducible, and it never blanks a provider
  it cannot read). Venice: **135/135 models priced**, and the closed models finally have two routes:
  `claude-sonnet-5-5`, `claude-opus-5`, `gemini-3-8-flash`, `grok-4-7`. Matrix 43→52 rows, 14→18 base models.
- The finding survives the model being proprietary: **`claude-opus-5` is $5/$25 per million on both
  priced routes and answers in 1.25 s vs 2.19 s (1.75x)** — a price table calls those identical.
- **Two OpenRouter prices had rotated since the 17th** (`deepseek-v4.1-flash` $0.0536→$0.0648;
  `deepseek-v4-flash-0731` $0.10→$0.0151 in, $0.30→$0.45 out). Every table that quoted them was
  regenerated; `routes/emit_routes_snapshot.py` now derives the delivery engine's price snapshot from
  `matrix.json` instead of a hand-typed copy, and CLAIMS.md carries all three rows.
- A test proved the guard works: the engine matched only one spelling of a model, so `gemini-3.8-flash`
  (how the provider writes it) missed the `gemini-3-8-flash` anchor. Dot and hyphen are now the same
  separator, with a check that both spellings reach the same comparison.
- **The re-measurement also moved the headline number, and four money pages were still quoting the old
  one.** The largest input-price spread is now **29.1x** (`deepseek-v4-flash-0731`: $0.0151/M against
  $0.44/M) where the pages said “up to 20.5x” — only the routes page was guarded, so the front door,
  the offer, the preview and the intake could keep a stale maximum indefinitely. `routes-page.py` now
  recomputes that maximum and requires it on all four (verified by breaking one of them).
### 6.4 One correction to the paper you should know about
The cache sentence in §10 said “6 of 8 probed routes” — from before the probe was extended. The probe
has 21 routes: **12 reported a hit, 6 did not, 3 unreadable** (2×429, 1 no field). Fixed, together
with the route counts (18 base models / 46 pairs) and the re-measured price row.
### 6.5 The one thing this shift could not do
`pi-web-tps-monitor` is **not on npm**, so it cannot appear in the Pi package catalogue
(`pi.dev/packages` indexes the `pi-package` keyword on npm) — the channel that reaches exactly the
people who run agent fleets. Verified end to end on a copy: `npm ci` + `npm run build` +
`npm pack` all exit 0 (25 files, 64.6 kB, no internal paths, no secrets, manifest conforms). Blocked
only by a **publish token**: `(espera-llave: NPM_TOKEN)`. **The name is unclaimed**, so publishing
also protects it. Command + checklist: `/home/vuos/code/p4/e097-night-worker/sales/publish-plugin.md`.
### 6.5 The front door was quoting a fleet window nobody could download (fixed)
The homepage, the offer and the published sample deliverable all quoted “our own fleet”: **8.7 s wall
per turn, 34% model / 29% tools / 37% unaccounted, 4.4% wasted (22 of 500), worst turn 85 s**. Those
numbers came from the live turn log, which **rotates** — so the window behind them was gone, and the
file the pages point at as public (`fleet/` in the repo, which §9 describes as a deliberately heavier
window) says something else: **median 7.2 s, mean 16.3 s, 25/23/52, 3.2% wasted (16 of 500), worst
300 s**. A published number a reader cannot reproduce is the exact failure this pack exists to catch,
so the pages now quote the published window, the sample fixture matches it, and a new suite
(`tests/fleet-window.py`, the 12th) recomputes the window from the JSONL and fails on drift. Paper §9's
p50 was also off by a rounding (7.245 s, printed 7.3 → 7.2).
### 6.6 And the offer now says the closed models are inside the coverage, with a number to match
The re-measurement also moved the headline price spread: the maximum is now **29.1x**
(`deepseek-v4-flash-0731`: $0.0151/M against $0.44/M) where four money pages said “up to 20.5x” —
only the routes page was guarded, so the front door, the offer, the preview and the intake could keep
a stale maximum indefinitely. `routes-page.py` now recomputes that maximum and requires it on all four
(verified by breaking one of them).
### 6.7 State of the servers, resolved live at 10:0xZ
- https://focalis.cc/ · /audit/ · /audit/preview/ · /audit/sample/ (and /audit/sample/cuts.html) ·
  /audit/routes/ · /audit/intake/ · /tps/ · /tps/article.html · /tps/audit/ — **all 200**;
  /company /terms /privacy /refunds /contact 308→200.
- Containers `focalis-caddy` (up 4 h, healthy) and `focalis-admin` (up 7 h, healthy). PI WEB session
  daemon **pid 353731** on :8504 — I did **not** touch it, and I did not restart Caddy either: every
  change this shift was served from the read-only mounts.
- host IPs: **192.168.0.177** (LAN), **100.102.52.59** (tailscale).
- **13/13 suites green** (`cd /home/vuos/code/p4/e097-night-worker/sales && python3 tests/all.py`), live URLs, verified
  twice, plus each new guard verified to FAIL when the value it protects is broken.
- Spend this shift: **~$0.10** (28 provider calls for the new measurements + browser tests). No
  secret printed, no account created, nothing deleted; the only new mail behaviour is none — I read
  the inbox, and there was nothing new in it (no HN answer, no lead).

### 6.8 The tail of the shift, in one line each
- **The paper's claim 1 quoted the value its own errata corrected**: "zero 3.06 s" is that cell's
  *mean*; the median is 3.05 (3.055) and the table below it already said 3.05. Its range was also
  ~2.5–3.5 where the six per-cell medians run 2.42–3.36. Fixed, and the test now reads the six
  medians out of `bench.csv` and requires them in claim 1.
- **Two alerting mechanisms were described with one number**: the home and the offer said the retainer
  alerts at "20%" for the floor, the miss rate and the waste rate, while the gate we actually ship
  fires at **+20% wall or 5% wasted turns**. Both pages now separate the two, and the test imports
  `regression_gate.py` and requires its constants (not a hand-typed threshold).
- **`article.html` could go stale** (it is generated from `REPORT.md` and is the copy people share);
  the test now requires the same §10 counts and cache count in the HTML.
- **"1,000 no-op turns ≈ 50 min" next to "3.14 s median"**: 1000 × 3.14 s is 52.3 min, so 50 was a
  rounding of the same quantity that the offer already wrote as 52. Both say 52 now.
- **`article.html` is checked for staleness** now (it is generated from `REPORT.md` and is the copy
  people share; editing one and not the other is how a superseded sentence survives).
- **The published tests no longer carry this machine's paths.** R45 established that rule, then
  `paper-matrix.py` and the three suites added tonight baked `/home/vuos/srv/tps` and
  `/home/vuos/code/p4/e097-night-worker/report-pub` back in. They now resolve the repository from `REPO_ROOT` or their own
  directory, and otherwise read the **live copy** of it over the network, so a fresh clone runs them
  as-is. `git grep "/home/vuos\|/home/vuos/code/p4/e097-night-worker" tests/` in the public repo is empty again.
- **The site's own repository was two months behind its working tree** — and that tree is what the
  containers serve: the Caddyfile (clean URLs, the `/tps/` and `/audit/` mounts, the handler that keeps
  the payment pages off the active landing), `ACTIVE` and the `variants/active` symlink (which decide
  what the site root *is*), the compose file that wires lead notifications, and both variants. A
  `git reset` would have left the domain without a front page. Committed and pushed
  (`g8d3/focalis.cc`, `2c2ae23`); the 35 MB of taste-loop screenshots are ignored (reproducible with
  `tools/capture.py`), and the pre-commit secret sweep was clean.
- **One test I wrote this shift was itself wrong** (it compared `#limits` from the CSV render with the
  demo's waste count — it passed only while both were zero) and one suite was flaky for the same kind
  of reason. Both fixed; that is why the pack's rule is "verify a new guard fails when it should".

## 7. Fifth shift (11:0xZ → 12:0xZ) — one real correction with money in it, and HN's real verdict

### 7.1 The boot lever we sell was 2.5x smaller than the number we published (fixed, deployed)
This is the item worth your attention. The pack's one sellable, removable lever is the process
boot, published everywhere as **929 ms** ("65 wall-hours a year for a 10-loop fleet"). Section
§5.4 of the paper rested on a measurement whose **raw data was never kept**. I re-ran the exact
same command on the same machine: **371 ms**. Not a typo, and not noise — the two model-catalog
fetches an extension performs at startup were inside that 929 ms window. We cached them for six
hours (that was R2, back on the 17th), so the same command measures three times faster now;
forcing the fetches back on reproduces 940 ms, which is the proof of what the difference is.

What changed, all deployed and guarded:
- the paper keeps the 2026-10-17 column and adds the 2026-10-18 pair (**372 ms warm / 940 ms
  cold**), with the cause named;
- the home page's boot card, the lever paragraph, the offer, pricing, the intake's process-model
  question, the preview's two caveats, `roi.py`'s default, the sample deliverable and the four
  Tier-2 examples all moved to the measured pair — the lever is **26 wall-hours a year, not 65**
  (65 is the cold figure);
- new published artifact `procsplit/`: the reproducer plus both raw runs (5 and 3 reps, per-rep
  timestamps), and a new suite (`tests/procsplit-claims.py`) that recomputes every median from
  the per-rep marks and fails if any page quotes the other number. I verified the guard fails on
  a mutated §5.4 row before trusting it.
- `CLAIMS.md` records the correction on the three affected rows.

Why it matters commercially: every hour of a lever we cannot actually deliver is a number a
prospect can check against their own machine. The honest version is still a real lever (a fleet
that keeps a process warm saves 26 h/year at 10×100, before any model call) and it now has raw
evidence anyone can download, which is a better sales asset than the bigger number was.

### 7.2 Hacker News: the shadowban is lifted for the profile, NOT for comments (measured, closed)
hn@ycombinator.com evidently acted: `news.ycombinator.com/user?id=focalis` now answers an
anonymous visitor (it said "No such user." yesterday) with karma and the paper in the bio. So I
posted — from our own account, in the thread about the model we actually run — a **140-word
comment with no link, no pitch and no offer**, four measured numbers. **It was dead within 20
seconds** (`dead: true` via HN's own API, shown as `[flagged]` to anonymous readers). The
previous comment, the one with the link, is dead too. Two comments, two styles, both killed ⇒
the restriction is on the account, not on what we wrote.

So: **do not spend your morning on HN.** If you want this channel, answering the email thread
with this evidence ("accepted with a 200, profile visible, item `dead` in 20 s with no link") is
the only remaining move — ask them to lift the *comment* restriction explicitly, not just the
profile one. The material for it is still ready in `sales/outreach-targets.md`.

### 7.3 The admin panel thought the live site was the 3D game (fixed)
`/admin/status` answered `"active": "variant-d-world"` — the game, described in the panel as "No
direct sales — studio showcase" — while `https://focalis.cc/` was serving the page that sells. The
symlink was switched when the landing was deployed but the `ACTIVE` file the panel reads first, and
the hardcoded variant map, were never updated, so the landing could not even be listed. Anyone
opening the panel would have believed the wrong page was live, and any script re-applying `ACTIVE`
would have reverted the front page. Fixed (ACTIVE + map + a 2-second `focalis-admin` restart) and
verified: the panel now reports `variant-e-landing`, the root still serves the landing, the lead
endpoint still answers.

### 7.4 Everything else this shift
- Re-ran the price collection (`routes/collect_models.py`) as the shift's first job: one
  non-anchor price rotated (glm-5.3 completion on OpenRouter), **no published row was stale**.
  Added a guard for exactly that class (`tests/matrix-prices.py`): it recomputes each published
  route price from the providers' own catalogs and fails naming the row.
- Read the mailbox: no HN reply yet when I started, no real lead (all messages are our tests).
- Committed/pushed: the route-price guard, the paper's raw-data artifact and its two new links,
  the claims update, and a `.gitignore` (the tests drop `__pycache__` into the repo).

## 8. Sixth shift (13:30Z → 15:2xZ) — two provider prices rotated under eight published pages, and a GPT fleet can now read itself into the offer

**Nothing needed from you in this shift.** No new keys, no purchases, no decisions. The lead
mailbox was read (no answer from hn@ycombinator.com, no real lead — everything after 04:04Z is our
own test mail) and the channel work stays where shift 5 left it.

**1. Two OpenRouter prices rotated overnight and made eight published pages stale — the guard
caught it, which is the point of the guard.** Re-running `routes/collect_models.py` (the free step
that nobody can automate) showed `deepseek-v4.1-flash` at **$0.04/M** input (was $0.0648) and
`deepseek-v4-flash-0731` at **$0.0199/M** (was $0.0151). Both are anchors of the measured matrix,
so the "up to 29.1x" headline the four money pages quote was wrong: **the real maximum is 22.1x**.
`tests/matrix-prices.py` (added in the fifth shift) failed naming the two rows before I touched
anything. Every table was then regenerated from a fresh measurement — the paper's §10 table, its
TL;DR, `article.html`, the routes page, the home, the offer, the preview, the intake, the claims
audit — and **the four Tier 2 examples were rebuilt together from one window** so the cut list a
client reads cites the live price (it quoted $0.0648/680 ms; now $0.04/1728 ms and a **$1,169/year**
difference instead of $1,094). Nothing was published by hand: every number comes from a script.

**2. A GPT fleet now gets a route comparison instead of an honest refusal.** OpenAI models only
had one priced route (OpenRouter), so a GPT client was told "not in our matrix" while Claude,
Gemini and Grok were covered. Venice prices them too, so four anchors were added and measured:
`gpt-5.4`, `gpt-5.6-luna`, `gpt-5.5`, `gpt-4o`. **Every one charges the identical list price on
both routes** and the first token still differs — `gpt-5.4` 1124 ms vs 1726 ms (**1.54x**),
`gpt-4o` 1332 vs 872 ms (**1.53x**). Matrix is now **22 base models / 54 route pairs**, the
delivery engine prints that comparison for a GPT client, and the offer quotes it. (A test that
used `gpt-5.5` as the example of "a model outside the matrix" silently stopped testing that shape
when the anchors were added; it now uses a model no provider we hold a key for serves, and there
are 5 new checks for the OpenAI case.)

**3. The free preview now says whether *your* models are on routes we measured.** Section 2b of
https://focalis.cc/audit/preview/ matches the model names in the log you drop in against the
measured matrix (same normalisation the engine uses, so `openai/gpt-5.4`, `gpt-5-4` and `GPT-5.4`
all reach the same row) and shows the routes we measured, the input-price spread and the
first-token spread — or says the model is outside the matrix, with the number of base models we
cover. Zero network requests, no dollar amount anywhere on the page (a ratio needs no rates from
you; a saving does, and that is what the audit prices). The parity test now reads the matrix from
**the served page**, not from the local build — that hole would have let a stale embedded matrix
ship.

**4. One real defect the suites found in a page we had already "fixed".** `preview-parity` failed
on its own boot check: **both caveats on the free preview still sold 929 ms**, the cold-cache
number that the fifth shift retracted (the honest pair is **372 ms warm / 940 ms cold**), and said
65 wall-hours a year instead of 26. The shift-5 guard had passed because it looked for the string
"372" anywhere on the page, and "372" also occurs in the embedded demo rows as an output-token
count — a textbook false positive. Both caveats are fixed and the check is now anchored on the
sentence and verified by breaking it (mutilating the served file for 5 seconds made the three new
checks fail; restoring it made them pass).

**5. The four Tier 2 example deliverables are now reproducible — and publishing their window
nearly leaked a private field.** The examples at `/audit/sample/` (the filled cut list, budget,
cache report and size curve a prospect reads) came from the **live** turn log, which rotates: the
window behind their figures disappeared and nobody could check them (the same class as §7.1's
numbers). They are now a function of three published files — `fleet/fleet-turns-2026-10-18.jsonl`,
`fleet/fleet-history-2026-10-18.jsonl`, `fleet/example-answers.json` — and the new suite
`sample-repro` downloads those, re-runs the delivery engine and compares the four served pages
(undoing only the two things the host adds: its analytics script and its rewriting of the contact
link, which the test decodes back to `hello@focalis.cc`).
While exporting that turn window I found that **the turn log started carrying `sessionName`** — the
private label of a session, in practice the text of the prompt that opened it — and the first
export published it into a file destined for a public repository. It was caught before any commit
(the 2026-10-17 window never carried it), `publish_fleet.py` now drops it from both exports, and
the repro test fails if either published window contains it.

**6. The cache probe went from 21 routes to 34, and found the cleanest case for the pitch.**
While adding the OpenAI anchors I found **five routes listed in the cache config that had never
been probed** (config and measurement had drifted). Measured: **22 of the 31 routes that answered
reported a cache hit**; the new headline is `gpt-4o` reporting **99.9% cached on one route and 0%
on another for the same model name at the same list price** — and `glm-5.1` 100% vs 0%. The honest
counter-example is in the same table: `glm-5.2` hits 98–99.8% on both routes and on one of them the
wall got **worse** (2.7 s → 8.9 s), which is why we do not sell cache discipline. The page now says
how many probed routes could not answer at all, so its "22 of 31" and the paper's "29 of 34
readable" cannot be read as a contradiction.

**Server status, resolved live at 16:2xZ** (nothing was restarted this shift): `focalis.cc/` 200
19.9 KB · `/audit/` 200 45.8 KB · `/audit/preview/` 200 160 KB (the new section) · `/audit/sample/`
200 · `/audit/routes/` 200 27 KB · `/audit/intake/` 200 · `/tps/` 200 · `/company` `/terms`
`/privacy` `/refunds` `/contact` → 308 to the clean URLs, all 200 after the redirect · `/world/`
200 (the game, nothing lost). Containers `focalis-caddy` (Up 10 h, healthy) and `focalis-admin`
(Up 4 h, healthy). PI WEB session daemon **pid 353731** on :8504 (not touched). Host IPs:
**192.168.0.177** (LAN) and **100.102.52.59** (tailscale).

**Evidence**: `cd /home/vuos/code/p4/e097-night-worker/sales && python3 tests/all.py` → **16/16 suites green** against the
live URLs (the shift added `sample-repro`; several runs, because four guards were rewritten and
each was verified by breaking it first). Commits: `8d08e45`, `86d4f31`, `1722d9e`, `59db21e`,
`8cab3ee`, `60d2ff1`, `545826b` in `g8d3/transcript-tax` and `75ab31a` in `g8d3/focalis.cc`.
Spend this shift: **≈$0.08** (15 route re-measurements, 8 new route measurements, 26 cache probes,
browser tests). No secret touched, no purchase, no account, nothing deleted.
