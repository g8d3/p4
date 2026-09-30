# ScrapeNet LAUNCH KIT — first 10 users

Live collector (from `needs.json` `public_url`, tailnet-first): **http://100.102.52.59:8383**
Shareable example dataset: **http://100.102.52.59:8383/dataset/product-prices**
Extension zip: **http://100.102.52.59:8383/download/extension.zip**

> If the tailnet URL changes, run `bash bin/serve.sh` — it rewrites
> `needs.json:public_url` and prints the fresh URLs.

## The 5-minute pitch (use everywhere)

ScrapeNet turns websites you already visit into paid public APIs. Install the
extension → scrape → publish → every accepted record earns 0.01 SCRAPE, and
every dataset gets a shareable page like the one above. Invite friends with
your referral code and you earn 20% of the platform commission on their
records — they keep their full payout.

## Copy-paste content

### X thread (5 posts)

1/ Websites you visit daily are worth money as data. I built ScrapeNet: a
browser extension that turns any page into a public JSON API — and pays YOU
per record. Live demo dataset: http://100.102.52.59:8383/dataset/product-prices

2/ How it works: install the extension (unzip + Load unpacked, 2 min), sign
up on the dashboard for a node id + token, enable a host, hit Scrape now.
Your rows show up live. Then Publish → your data gets a shareable page.

3/ The twist: every published dataset is a landing page. Post it on Reddit,
Discord, X — anyone can read the API free, and anyone who signs up via your
?ref= link earns you 20% of the platform commission on their records. Forever.

4/ Example: 1,000 price records = 10 SCRAPE gross. Refer 5 friends doing the
same and you skim commission on 5,000 records without scraping yourself.
Leaderboard is public: http://100.102.52.59:8383/api/leaderboard

5/ Try it in <5 min: download http://100.102.52.59:8383/download/extension.zip
→ dashboard has the 3 steps. First 10 users: reply with your dataset page and
I'll feature it + send bonus test records your way. Who's in?

### Reddit post → r/webscraping

Title: I built a scraping network where the scrapers (you) own the datasets and get paid per record

Body:
I got tired of scrapers doing the work while someone else sells the API, so I
built ScrapeNet: a Chrome extension + collector where YOU publish the dataset
as a public JSON API and earn 0.01 SCRAPE per accepted record.

How a first run looks (under 5 min, no prior knowledge needed):
1. Download the extension zip from the dashboard and Load unpacked it.
2. Sign up on the dashboard (one field: your name) → node id + token.
3. Enable a host, Scrape now, then Publish. You get a shareable dataset page,
e.g. http://100.102.52.59:8383/dataset/product-prices — post it anywhere.

There are 3 built-in recipes (product prices, job listings, crypto ticks) and
a sandbox that statically checks your transform before saving. The collector
is stdlib-only Python; reads are public, writes need your token.

Referral loop: every dataset page carries ?ref= codes — invitees earn full
payouts, you get 20% of the platform commission on their records. Honest
question for this sub: what dataset would you publish first if the API paid
you per row? Dashboard: http://100.102.52.59:8383

### IndieHackers post

Title: ScrapeNet — I turned web scraping into a referral game where users own the APIs

Body:
Hypothesis: the hardest part of a scraping business isn't the scraper, it's
distribution. So instead of selling datasets myself, I built ScrapeNet, a
network where users scrape (browser extension), publish (one click → public
JSON API + human share page), and earn per record (0.01 SCRAPE, 10%
commission).

The growth mechanic IS the product: every published dataset is a landing page
(stats, sample rows, copy-API-link button) with the publisher's referral code
embedded (?ref=). Visitor → signup → both earn. The leaderboard
(/api/leaderboard) makes it competitive.

Stack: zero-dependency Python collector + vanilla MV3 extension. Auth is
self-serve signup → token; reads stay public.

Ask: I'm hunting users 1–10. If you have a niche dataset in your head (prices
in your country, jobs in your stack, anything), I'll personally help you
publish it this week. Dashboard: http://100.102.52.59:8383 — what would make
you publish your first dataset?

## Directory checklist

- [ ] Chrome Web Store listing — [NEEDS OWNER]: requires a Google developer
  account ($5 one-time), app icons/screenshots, and the zip in
  `/download/extension.zip`. I cannot pay or accept store ToS for you.
- [ ] Product Hunt launch — [NEEDS OWNER]: needs a human account, tagline,
  and maker comment. Draft tagline: "Turn any website into a paid API".
  I cannot post from your account.
- [ ] AlternativeTo entry — [NEEDS OWNER]: human account + 2–3 screenshots
  of the dashboard and a dataset page. I can generate the screenshots on
  request but cannot submit them.
- [ ] r/webscraping post (draft above) — [NEEDS OWNER]: post from a warmed
  human account; check sub rules on self-promo first (message mods if unsure).
- [ ] r/SideProject + r/beermoney posts — [NEEDS OWNER]: same, human accounts.
- [ ] Discord servers (webscraping / data-hoarder / indie-hacker communities)
  — [NEEDS OWNER]: join + read #promo rules; several ban links outright.
  I cannot join servers or read their rule channels for you.
- [ ] X thread (draft above) — [NEEDS OWNER]: post from the owner account;
  pin it, reply to every comment in the first 24h.

What I already did (no owner needed): install path works from a cold URL,
signup is self-serve, dataset pages + leaderboard are live, this kit is
written. Anything above without [NEEDS OWNER] I can execute — tell me to.

## Referral / UGC loop

```
publish dataset → share /dataset/<id>?ref=CODE anywhere
→ visitor reads free data, clicks Join/Sign up (code pre-filled)
→ POST /api/signup {name, referral_code} attributes referred_by
→ invitee earns full net per record; referrer earns referral_pct %
   of the platform commission on every referred record (needs.json:
   commission_pct=10, referral_pct=20 → referrer gets 2% of referred gross)
```

What to measure (first 10 users):

| Metric | Where it shows | Target w1 |
|---|---|---|
| signups | `data/auth.json` node count, audit `signup` events | 10 |
| referral rate (% signups with referred_by) | `/api/leaderboard` totals.referred_signups | ≥40% |
| datasets published | `/api/published` count | ≥5 |
| referred records | `/api/leaderboard` totals.referred_records | ≥200 |
| referral paid out | `/api/earnings` totals.referral_paid | >0 (loop closed) |

Dashboard surfaces: §5 Referral leaderboard panel (live from
`/api/leaderboard`), §4 Earnings board (per-node `referral_earnings` +
totals `referral_paid` / `platform_commission`).
