# Domains — ranked shortlist (checked 2026-09-29, NOT purchased)

## Proposed umbrella brand: **Everloop**

One brand over both apps: e082 is a loop that never stops, e083 is a network
of nodes in a loop (capture → publish → earn → repeat). Tagline-ready:
*"Everloop — agents that keep going, networks that pay."*
`everloop.com` is taken, so the brand plays as **everloop.cc** (+ defensive
`.com` variant below). Owner approval needed before any brand commitment.

## Availability method (read-only, no purchase)

`curl -sL https://rdap.org/domain/<name>` — HTTP 404 = no RDAP record
(likely available, **confirm at checkout — RDAP absence is not a guarantee**);
HTTP 200 = registered. 14 names checked across two batches.

## Prices (Porkbun public TLD pages, fetched today — registrar of choice, not a purchase)

| TLD | Registration | Renewal | ≤$15/yr? |
|---|---|---|---|
| `.com` | $11.08 (everyday) | $11.08 | YES |
| `.cc` | $3.40 (first-year sale) | $8.55 | YES |
| `.io` | $28.12 (first-year sale) | $51.80 | **NO — excluded** |

`.io` fails the ≤$15/yr bar even on sale, so no `.io` names are shortlisted
despite the preference order. Revisit `.io` only if the budget moves.

## Ranked list

| # | Domain | RDAP | Price/yr | Why this rank |
|---|---|---|---|---|
| 1 | **everloop.cc** | 404 available | $3.40 yr1 → $8.55 renew | Exact brand match, cheapest, short |
| 2 | **everloopagent.com** | 404 available | $11.08 | The `.com` trust anchor for the same brand; longer but unambiguous |
| 3 | **keeploop.cc** | 404 available | $3.40 yr1 → $8.55 renew | Backup brand, matches e082 "keep-going" language |
| 4 | **foreverloop.cc** | 404 available | $3.40 yr1 → $8.55 renew | Backup brand, matches e082 product name directly |
| 5 | **meshloop.cc** | 404 available | $3.40 yr1 → $8.55 renew | Backup brand, leans e083 network side |

Also available but cut: `loopgrid.cc`, `everagent.cc`, `netloop.cc`
(weaker names). Taken (do not pursue): `everloop.com`, `keeploop.com`,
`agentloops.com`, `scrapefeed.com`, `loopwork.com/.cc`, `scraploop.com`,
`meshloop.com`, `everagent.com`, `netloop.com`, `loopmesh.com`, `keeploops.com`.

Strategy: buy #1 for brand + #2 for `.com` credibility, point both at the same
landing page; keep #3–#5 as fallbacks, not purchases.

## Exact purchase steps for the owner (DO NOT delegate — purchase needs owner payment)

1. Go to `https://porkbun.com` and **create the account yourself**
   (agents must never create accounts).
2. Search `everloop.cc` → add → checkout (~$3.40 + free WHOIS privacy).
3. Search `everloopagent.com` → add → checkout (~$11.08).
4. In Porkbun dashboard → DNS (Cloudflare-powered, free): point records at
   this box, or use **URL Forwarding** (free) to the tailnet URLs as a
   day-one shortcut.
5. Free Let's Encrypt SSL via Porkbun; verify both names resolve before announcing.
6. Tell the agents the chosen names → we wire them into `needs.json`
   (`public_url`) and the outreach copy. Estimated total day-one: **~$14.48**.

Nothing has been bought, no account created, no money spent.
