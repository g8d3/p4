# e041 — Web Access for Agents + the outbid.lol frenzy

**Goal**: document what this session learned about how an agent can (and cannot)
reach arbitrary web pages, and record the concrete test case: the outbid.lol
pay-to-rank leaderboard trend of August 2026 and its clone wave.

Why: the user asked two things at once — (1) how to access any website without
getting blocked (captcha, fingerprinting, proxies, user-agent) and (2) a live
test of whether my own web tools can reach a brand-new trending site (outbid.lol)
and every clone of it. The answers turned out to be the same knowledge, and this
experiment is where it lives so future runs inherit it.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, data formats, conventions

## The core finding (2026-08-23 session)

My web surface is **two different tools, and only one of them actually visits
pages**:

| Tool | What it is | Blocks it |
|---|---|---|
| `web_search` | Server-to-server indexed search API (Bing/Google/Tavily-style). Returns title + url + snippet only. | Nothing — it never touches the target site. |
| `web_fetch` | Server-side HTTP fetch that converts HTML → markdown. This is a real web client. | Everything a basic client hits: 5xx, rate-limit, captcha, anti-bot. |

So "I have no problem searching social networks" was misleading: `web_search` is
an index, not a browser. `web_fetch` is the blocked client. Two concrete, honest
data points from this session:

- **Reddit `/r/SideProject`** and **buildmvpfast.com** → `504 upstream error`
  (twice each). Anti-bot / throttling. Could not read them directly.
- **X `/i/trending/...`** → `200`, but the content is a **Grok-generated
  summary** ("This story is a summary of posts on X … Grok can make mistakes"),
  not the raw posts.

The user's original intuition was correct: there is no silver bullet. To reach
hard sites (Reddit, X, TikTok, Instagram) reliably you need a **stack**, not one
tool. The stack, in increasing order of robustness:

1. **User-agent + header spoofing** — cheapest, only beats weak protections.
2. **Anti-detect / stealth browsers** —
   `Camoufox` (open-source, Firefox-based, the best free option) or
   `Playwright`/`Puppeteer` with `playwright-stealth` /
   `puppeteer-extra-plugin-stealth`. Hides composite fingerprint, not just UA.
3. **Residential rotating proxies** — Bright Data, Oxylabs, Smartproxy, SOAX.
   The layer with the most impact on captcha + IP blocks.
4. **Anti-detect browsers (paid)** — Multilogin, GoLogin, AdsPower,
   Dolphin{anty}, Kameleo, Incogniton, MoreLogin.
5. **Captcha solvers** — 2Captcha / CapSolver, only when the above fail.

Working recipe today: **stealth browser + residential rotating proxy +
cookie/session persistence (+ captcha solver as fallback).** User-agent switching
alone is obsolete once an anti-detect browser rotates the whole fingerprint.

## How to reach a fragile site (lessons, learned here)

The pragmatic way to get content that `web_fetch` cannot get:

1. Try `web_fetch` on the target. If it blocks (5xx/captcha), **don't retry in a
   loop** (retry cap = 3).
2. Use `web_search` to find **mirrors/syndicated copies**: the same story
   re-published on blogs, Medium, case-study sites. Those usually load fine.
   (Example: Reddit r/SideProject blocked, but quvir / gittube / foundershut /
   partnerkin re-published the same numbers and were fetchable.)
3. If the content is a static SSR page, `web_fetch` is enough (as with the whole
   outbid.lol clone wave).

## The outbid.lol test case

Full findings live in `output/findings-outbid.md`; clones are in
`output/clones.csv`. The headline:

- **Also known as**: the `.lol bidding directory frenzy of August 2026`.
- **Origin**: Jonathan Wilke (German indie hacker, also built supastarter)
  launched outbid.lol on **Aug 19, 2026, 11:08 PM CEST** after ~3 hours of work.
- **Mechanic**: pure pay-to-rank leaderboard. Highest bid = #1. Min bid $2,
  whole dollars, ties to the older entry. List a product URL or an X handle.
- **First 24h** (self-reported, partly corroborated by third-party scrapes):
  $21,499 revenue, 200,000+ visitors, highest single bid $10,000, 1,500+ new X
  followers, a declined $100k acquisition offer, 3–10+ direct clones within hours.
- **By day 3**: six-figure realized gross (The Index tracker read $132,940 →
  $139,058 on Aug 22 from the operator's `/api/revenue`), dozens of clones,
  meta-directories that rank the other bid boards, and even a paid template
  (`shadcn-labs/outbid-template`) to clone it.
- **Key distinction**: standing bids on the visible board ≠ lifetime revenue.
  The board shows what's currently committed to displayed spots; realized gross
  includes every outbid/rolled-over payment. The gap widens as the board churns.
- **Why .lol**: 1st-year `.lol` registrations were ~$0.99 in Aug 2026 and wide
  open; the TLD signals "fast, funny, low-stakes experiment."

### Clone models (the mutation wave)

| Model | Example | How it differs |
|---|---|---|
| Pure bidding | outbid.lol, growu.lol, puremoney.lol | Highest bid wins, continuously. |
| Reverse / Dutch auction | lowbid.lol, undercut.lol | Lowest *unique* bid (or undercutting) takes top — removes rich-founder edge. |
| Luck / slot machine | payluck.lol | $9.95 list, random coupon locks your price forever; boards of 50, next board costs more. |
| Hybrid free + paid rank | bidboard.lol | Free dofollow listing floor; money only buys position (SEO-safer). |
| Territory / map | warmap.lol | Bid to conquer countries on a world map. |
| Scarcity + decay | lastspot.lol | Hard cap of 100 spots, value decays 5%/day. |
| Head-to-head | pitchpit.lol | Pay for a place in matchups, not for the outcome. |
| Meta / self-referential | biddirectory.lol, bidding.lol | A directory that ranks the other bid boards by bid. |
| Vertical | topapp.lol (apps), xbid.lol / xme.lol (X handles) | Same mechanic, niche audience. |

### SEO reality check (the important part for anyone spending money)

- Almost every clone is a domain registered this month — DR < 10–20 at birth,
  no organic traffic of their own.
- **Pure pay-to-rank flirts with link-scheme territory.** Google's spam policies
  treat links bought for ranking as manipulation, and SpamBrain got an upgrade
  the same week. A board that literally shows "this link cost $400" is the most
  legible paid-link footprint possible. Free-listing / badge models are much safer.
- Counted as *launch distribution* (short-term traffic + a small early-equity
  lottery ticket), it can be worth $5–$50 of experiment budget. Counted as *link
  building*, it is not.
- Watch effective CPC, not rank; the click counter on outbid.lol resets on the
  hour, and high-click listings show near-zero correlation with the site's own
  traffic (advertisers driving their own audience).

## Access-reachability results (this session)

All targets returned `200` via `web_fetch` (no blocks):
`outbid.lol`, `outbid.lol/about`, `outbid.fyi`, `payluck.lol`, `lowbid.lol`,
`saascity.io/blog/...`, `github.com/shadcn-labs/outbid-template`.

Clones still live/reachable and worth tracking live: `outbid.fyi` lists 173
boards ("updated 1 hour ago") and ranks them by revenue as its own content.

## Data files

| File | Contents |
|---|---|
| `output/findings-outbid.md` | The full outbid.lol / clone-wave analysis (narrative). |
| `output/clones.csv` | Clone sites with model, launched date, revenue/status where known. |
| `output/access-reachability.md` | Which targets `web_fetch` reached vs blocked. |
| `trail.md` | Session history / decisions. |

## Sources (web research this session)

- [outbid.lol/about](https://outbid.lol/about)
- [outbid.fyi (clone directory)](https://outbid.fyi/)
- [SaaSCity — .lol bidding directory frenzy](https://saascity.io/blog/lol-bidding-directory-frenzy-outbid-payluck-2026)
- [shadcn-labs/outbid-template (clone kit)](https://github.com/shadcn-labs/outbid-template)
- [payluck.lol (luck variant)](https://payluck.lol/)
- [lowbid.lol (reverse auction)](https://lowbid.lol/)

## Notes

- The clone wave is a moving target: new boards launch hourly and half will go
  quiet. The `findings` and `clones.csv` are a snapshot (this session), not a
  live feed. Re-run the research to refresh.
- Do **not** spend real money on any of these boards without re-reading the SEO
  reality check above; the durable value is in established, reviewed directories.
