# e108 — vertical clone leads

**Goal**: the sourcing half of the "clone the bloated vertical SaaS" play (owner link,
x.com/timchaoai/status/2119907509494591859): find businesses that already pay $24k–36k/yr
for ServiceTitan / Mindbody / Housecall Pro / Jobber-class software and hate it, so a
one-time $15k private rebuild (3 workflows, no monthly licence) is obvious to them.

**What it is worth**: the build half of that play is cheap for us (agents do it). The half
that decides whether it ships is a list of named businesses, which is what this experiment
produces — or proves it cannot, measurably.

## Measured (2026-11-10, first run)

`python3 leads.py` — 4 verticals × 1★ and 2★ Trustpilot through real Chrome
(`agent-browser`): **101 pain-leads in ~5 min**, dated and ranked:

| vertical | leads |
|---|---|
| Housecall Pro | 30 |
| Jobber | 26 |
| Mindbody | 23 |
| ServiceTitan | 22 |

**The finding that matters: 0 of 101 reviews name the business.** They give a first name,
a country and the complaint ("we are a small plumbing company… paying a premium… can't get
a real person on the phone"), never the company. G2 refuses us outright (`g2.com/products/…
/reviews` → empty challenge page, title `g2.com`), so the tweet's own recipe — filter 1★ on
G2, read the owner's name, title and company — does not survive contact from this machine.

So this experiment ships **pain intelligence, not contactable leads**. The extractor keeps a
`business` field and leaves it empty rather than guessing (ESTANDAR: unknown stays empty);
`data/leads.md` prints `unknown (review does not name it)` next to every one.

## Next step (the identity join, unbuilt)

Reviews answer "does it hurt and why". Identity + contact needs a second source joined by
vertical: **job postings** ("ServiceTitan experience required", city, company name, growth)
and **contractor licence lists** (public, full legal name + city + phone, no ToS problem).
Job postings are the stronger join: a business hiring for the tool is a business that uses
it, is growing, and has a budget — and unlike a review, it prints the company.

## Files

| File | What |
|---|---|
| `leads.py` | scrape → parse → rank → `data/leads-<date>.jsonl` + `data/leads.md` sheet. `--sheet` rebuilds the sheet from the newest jsonl. |
| `config.json` | verticals (vendor, Trustpilot URL, who they serve), pain `signals` mapped to the 3 workflows to rebuild, and the `offer` numbers. Nothing market-specific in code. |
| `data/` | latest leads (jsonl) and the human sheet (md). |

## Rules

- Standing rules apply. Nothing here writes to another system, sends anything, or contacts
  anyone: outreach needs the owner's explicit approval.
- Scraping legality is per-source and must be checked before scaling a source (Trustpilot
  serves public pages to a real browser; G2 does not allow it; licence lists are public
  data). Never put a scraped person's name in a file outside this `data/` dir.
- Keep the offer in `config.json`, never in code: the price is a market decision.
