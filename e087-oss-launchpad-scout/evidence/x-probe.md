# X.com probe — what is visible vs blocked (no invented content)

Date (UTC): 2026-10-05T14:56–14:58Z
Rule: every string below is quoted from live tool output. Nothing is paraphrased
into "trends". Blocked is recorded as blocked.

## Attempt A — tinyfish fetch https://x.com/explore — BLOCKED (login wall)

Command:

```bash
tinyfish fetch content get --format markdown "https://x.com/explore"
```

Raw result (JSON, exit 0 — the fetch itself succeeded, the CONTENT is a login wall):

```json
{"results":[{"url":"https://x.com/explore","final_url":"https://x.com/i/jf/onboarding/web?redirect_after_login=%2Fexplore&mode=login","title":"X - The Everything App / X","description":"From breaking news and entertainment to sports and politics, get the full story with all the live commentary.","language":"en","author":null,"published_date":null,"latency_ms":100.28,"format":"markdown","text":"We’ve detected that JavaScript is disabled in this browser. Please enable JavaScript or switch to a supported browser to continue using x.com. You can see a list of supported browsers in our Help Center.\n\nHelp Center\n\nTerms of Service Privacy Policy Cookie Policy Imprint Ads info © 2026 X Corp.\n\nSee what's happening\n\nSelect an option below:\n\nContinue with phone\n\nContinue with Apple\n\nor\n\nContinue\n\nBy continuing, you agree to our Terms of Service, Privacy Policy and Cookie Use."}],"errors":[]}
```

Honest reading: server-side fetch is redirected to the logged-out onboarding
flow (`/i/jf/onboarding/web?redirect_after_login=%2Fexplore&mode=login`) and
sees only the JS-disabled/login boilerplate. NO trends, NO posts visible.

## Attempt B — tinyfish fetch a guessed status URL — INVALID TEST (disclosed)

Command:

```bash
tinyfish fetch content get --format markdown "https://x.com/solana/status/1965000000000000000"
```

Raw result:

```json
{"results":[],"errors":[{"url":"https://x.com/solana/status/1965000000000000000","error":"page_not_found"}]}
```

Honest reading: the status ID above was GUESSED by the agent, not taken from
any real tweet — `page_not_found` therefore proves NOTHING about X access.
Kept here so nobody cites it as evidence. Real status URLs must come from a
rendered profile timeline (see Attempt D), not from invented IDs.

## Attempt C — agent-browser https://x.com/explore — BLOCKED (login wall, empty render)

Commands:

```bash
agent-browser open "https://x.com/explore" --session probe1
# => ✓ X - The Everything App / X
# =>   https://x.com/i/jf/onboarding/web?redirect_after_login=%2Fexplore&mode=login
agent-browser wait --load networkidle --session probe1
# => ✓ Done
agent-browser snapshot --session probe1
# => (empty page)
```

`eval "document.body.innerText"` returned `""` and `network requests
--type xhr,fetch` returned `No requests captured` (eval ran against a blank
context post-redirect; snapshot is the authoritative signal: empty page on the
login-onboarding URL).

Honest reading: logged-out Chromium is bounced to the same onboarding flow as
the server fetch, and nothing renders. NO Explore trends visible without login.
NOT quoted anywhere as trends.

## Attempt D — agent-browser https://x.com/solana (public profile) — WORKS logged-out

Commands:

```bash
agent-browser open --session probeX
agent-browser open "https://x.com/solana" --session probeX
# => ✓ Solana (@solana) / X
# =>   https://x.com/solana
agent-browser wait --load networkidle --session probeX
# => ✓ Done
agent-browser snapshot --session probeX
```

Raw profile header (verbatim from snapshot, 2026-10-05):

```text
- heading "Solana" [level=1, ref=e5]
- StaticText "@solana"
- StaticText "The high performance network powering internet capital markets, payments, AI agents, stocks, memes, and crypto apps."
- link "solana.com" [ref=e7]
- link "Joined January 2018" [ref=e8]
- link "3,682 Following" [ref=e9]
- link "4.2M Followers" [ref=e10]
```

First three timeline posts visible logged-out (verbatim StaticText runs):

1. (pinned order, timestamp "1h"):
   `BREAKING: ` + `@DGLD_Official` + `, the tokenized gold from Swiss refiner
   MKS PAMP, is now live on Solana.\n\nOver a million ` + `@swissborg` +
   ` users can buy it in the app from today, with liquidity managed by ` +
   `@ArrakisFinance` + `.`
   Engagement shown: 67 replies / 32 reposts / 211 likes / 48K views.
2. (timestamp "1h"): `See you tomorrow 🇸🇬` + repost of `@SuperteamSG`
   ("See you tomorrow" + 16-second video). 76 replies / 22 reposts /
   276 likes / 42K views.
3. (timestamp "3h"): `Just over 40 days to go till BREAKPOINT`
   (multi-media post). 128 replies / 28 reposts / 422 likes / 50K views.

Console during this render (verbatim): `[error] [GSI_LOGGER]: FedCM get()
rejects with NetworkError: Error retrieving a token.` — cosmetic, did not
block rendering.

Cleanup after: `agent-browser close --all`, `ps aux | grep "[c]hrome" | wc -l` → `0`.

## Honest summary

- VISIBLE: public profile pages (`/solana`) render logged-out in local
  Chromium with bio, follower counts, and recent posts + engagement numbers.
- BLOCKED: `/explore` (trends) and any logged-in surface redirect to the
  onboarding/login flow with an empty render — on BOTH pipes.
- NOT TESTED: search URLs (`/search?q=...`), hashtag pages, individual status
  pages from real IDs, `tinyfish agent run` against x.com (heavier/paid —
  deferred to Phase 2 if needed). No claim is made about them here.
- INVENTED NOWHERE: no trend, no post text, and no engagement number in this
  file comes from memory — all are pasted from the snapshots above.
