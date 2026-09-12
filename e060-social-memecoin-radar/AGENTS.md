# e060 — Social Memecoin Radar

Memecoin trading page where social volume / influencers matter most:
track mentions, velocity, influencer attention vs price/volume, and
surface rotation early.

## Hard dependency

Social data needs X access — see e041-web-access-agents (what works today)
and e056 P1 (browser/web-access capacity). No X pipe = no product.
Validate the pipe FIRST before any UI.

## Candidate sources (verify cost/coverage/ToS)

- LunarCrush (social metrics API), Kaito (mindshare), Dexscreener/GeckoTerminal
  (price+vol+txns, free tiers), X API (expensive — quantify), Telegram/Discord
  scrapes (ToS risk — flag, don't build on).
- e057-launchpad-trading (levels/math for entries, not discovery).

## Scope control

- v1: watchlist of 50–100 memes with social velocity + price spark + alerts.
  Paper-track calls before any live sizing.
- This is a discovery product; execution (if ever) reuses e052 rails.

## Spike result 2026-09-12 (subsession, web-verified)

X-ACCESS VERDICT: not feasible today — only index snippets + blocked
server fetch; documented recipe (Camoufox/stealth + residential proxy +
session persistence) unbuilt. Pipe-before-UI rule holds.
Costs: X pay-per-use reads $0.005/post (no free tier; Enterprise $42k+);
LunarCrush Hobby free = market data only, Individual $90/mo (10/min,
2k/day), Builder $300/mo; Kaito $833+/mo, API custom — OUT for v1;
Dexscreener FREE 300/min (best free tier). V1 stack: Dexscreener +
LunarCrush Individual, X credits sparingly. Biggest risk: X reads scale
linearly to unaffordable; if $90–300/mo can't fund velocity on 50–100
memes, kill or re-scope to Dexscreener-only rotation radar.

## Spike 2 result 2026-09-12: unofficial X read APIs (cheapest-first)

Official baseline $5.00/1k reads. Unofficial: twitterapis.com $0.04/1k
(cheapest, ≤20 tweets/call, 63 endpoints) > twitterapi.io $0.15/1k
(best documented) > Apify actors $0.15-0.50/1k (+30-50% overhead,
bad for polling) > SocialData.tools $0.20/1k > RapidAPI $0.50-5.50/1k
> Bright Data $1.50/1k+proxy. Zernio/Postproxy/xpoz = WRITE APIs (out
for reads). No counts-only endpoint anywhere — pay per tweet, count
client-side with tight limit=10-20 queries. Verdict: build on
twitterapis.com or twitterapi.io (~$4-15/100k tweets); LunarCrush $90/mo
wins if polling binds metering; all unofficial = ToS-grey, wrap behind
thin interface. Directory-of-crypto-social-networks noted as lead-gen
product feeding this radar.

## First tasks

1. X-access feasibility spike (e041 patterns, terminal-browser, costs).
2. LunarCrush/Kaito/Dexscreener API survey — free tier limits?
3. Define velocity score (mentions acceleration × influencer weight).
