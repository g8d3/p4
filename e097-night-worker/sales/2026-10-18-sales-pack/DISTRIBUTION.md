# Distribution — what is live, and the only channels left that need a human account

Written 2026-10-17 16:2xZ. Everything the agent could publish without an account is
published; what remains is posting to community accounts, which we do not have.

## Live now (verified with curl, 200)

| artifact | URL |
|---|---|
| the paper | https://focalis.cc/tps/ · https://g8d3.github.io/transcript-tax/ |
| the source repo | https://github.com/g8d3/transcript-tax (MIT / CC BY 4.0, topics set, homepage → report) |
| the offer page + calculator | https://focalis.cc/audit/ |
| the instrument's repo (funnel from pi users) | https://github.com/g8d3/pi-web-tps-monitor (README links the paper + offer) |
| contact | hello@focalis.cc (Cloudflare Email Routing → owner's inbox, verified) |

## Channels that need the owner's account (exact copy, 2 minutes each)

1. **Hacker News — Show HN** (needs an HN account; posting this is the single
   highest-reach free action available for this artifact)
   - Title: `Show HN: Where an agent loop's wall-clock actually goes (measured, with retractions)`
   - URL: `https://focalis.cc/tps/`
   - First comment (post it yourself, immediately): "Author here. 65 runs, 3 harnesses,
     one machine, ~8 cents of provider spend. The interesting part is what did NOT
     survive re-checking: cache state did not predict wall time, startup does not
     scale with the session store, and my size coefficient was 10x off its own table.
     All three are retracted in the paper, sections 6-8. Everything is reproducible
     from bench.csv + analyze.py in the repo, and `roi.py` will tell you the audit
     does not pay for itself on a cheap fleet."
2. **Reddit — r/LLMDevs** (or r/AI_Agents / r/LocalLLaMA, needs an account)
   - Title: `I measured where a "trivial" agent turn actually goes: 372 ms boot + ~1.5 s provider roundtrip + 3 ms model, and I had to retract three of my own findings`
   - Link: `https://focalis.cc/tps/`
   - Don't pitch in the post; the paper's last section links the offer. Answer the
     comments with the numbers.
3. **X** — the thread is written and validated (`/tmp/night/sales/thread.md`, 6 posts,
   all ≤280 chars, no cashtags) but **do not post it from @novaisabuilder**: that
   account has 3 followers and a Solana-risk bio, so a B2B cost-audit thread there
   reaches nobody and confuses the account. Post it from a technical account, or
   queue it only if that account grows an audience.
   Validator edit for a link-bearing variant: `publicar_x.py` refuses any text with
   `http` in it — that rule is why the thread has no link. If you want the link, the
   assert has to be relaxed deliberately, not accidentally.
4. **Direct outreach** — `/tmp/night/sales/outreach.md` has 3 emails + a DM and a
   "what not to say" list. There is no target list: sending from
   `zcash_cat@agentmail.to` would be ignored by anyone technical, so this needs you
   (a real address and a real name), not an agent.

## What NOT to do (and why)

- Do not post the thread from the bot account (see above).
- Do not mass-email from the agent inbox: `zcash_cat@agentmail.to` has no reputation
  and cold mail from it reads as spam.
- Do not buy traffic. The offer's credibility is "everything is checkable".
- Do not add the paper to awesome-lists as a PR: self-submission to curated lists is
  usually against their rules and the reputational cost is higher than the traffic.
