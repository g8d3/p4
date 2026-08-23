# e041 trail

## 2026-08-23 — Session start

### What the user asked
1. "How can I access any webpage without getting blocked (captcha, fingerprinting,
   proxies, user-agent, browser providers like Browserless/Browser Use)?" — they
   suspected there were many options and wanted the real picture.
2. "Prove it: find the latest trend of apps that made money fast in independent
   dev communities, grouped by source (X, Reddit, etc.) in a table."
3. Then: "Document what we learn this session in a new experiment. Then test
   whether you can reach **outbid.lol** and all its clones. I found it on X; it
   seems like a trend from the last 3 days."

### What we did
- Confirmed my web surface is two tools: `web_search` (index, can't be blocked)
  and `web_fetch` (real client, can be blocked).
- Proved it: Reddit + buildmvpfast gave 504; X trending gave a Grok summary.
- Researched the "made money fast" trend, grouped by source: X (Marc Lou's
  TrustMRR $29k/mo, DataFast $21k/mo...), Reddit (Next Starter AI $20k in 3
  months), Indie Hackers (Base44 $80M exit), blogs (Sebastian Roehl $602k).
- Researched outbid.lol and the whole `.lol bidding directory frenzy` of August
  2026. Reached outbid.lol, about, outbid.fyi, payluck.lol, lowbid.lol, the
  SaaSCity analysis, and the clone template directly with `web_fetch` — all 200.
- Created this experiment with AGENTS.md, findings, clones.csv, reachability.

### Key decisions
- Name: `e041-web-access-agents` — it's about how agents reach the web, with the
  outbid.lol case as the concrete test.
- Saved clones as CSV (per repo convention: prefer CSV over JSON for tabular).
- Treated the outbid clones as a live snapshot, clearly labeled, not a live feed.

### Honest caveats
- X trending content is a Grok summary, not raw posts; verification is limited.
- Revenue figures on clones are self-reported/third-party, unverified.
- The clone wave moves hourly; this is a snapshot.
