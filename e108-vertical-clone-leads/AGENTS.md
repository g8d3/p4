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

## At cost, measured (2026-11-10)

The $15k licence is what the tweet sells; it caps you at one salesperson per client. At cost
it is a distribution problem instead of a sales problem, and now the cost is a printed number.
`python3 costo.py` runs the three workflows against the cheapest real model we have
(`glm-5.3-flash`, $0.15/M in · $0.03/M cached · $0.50/M out, published rate) and prices the tokens:

| workflow | cold | warm (cached prompt) | tokens |
|---|---|---|---|
| quote-by-text | $0.00008 | **$0.00006** | 177 in / 128 cached / 77 out |
| estimate-to-paid | $0.00027 | **$0.00021** | 183 / 128 / 316 |
| revenue-report | $0.00018 | **$0.00015** | 214 / 192 / 293 |

A two-truck shop (6 leads/day, 4 invoices/day, 1 Friday report):
**$0.04 of inference per month**, $0.04 at cost + 15% network fee, against a
**$2,500/month** incumbent — ~62,000x. Real output, not a mock:

> Hi Dana, this is Dana's Air. We can be there today between 4:30 and 6pm. The diagnostic is 89,
> waived if you approve the repair. Fan running but warm air often means a failed capacitor
> (180-260) or fan motor (380-560), plus any refrigerant at 45/lb. Is the outdoor fan spinning,
> or humming without turning? That answer tells us the exact price before we start.

### What that number means (the honest part)

The licence is not a business: at $0.04/client/month there is no revenue to pay anyone, and a
$15k price is the only way this product earns — by refusing to scale. So margin has to come from
the **flow**, never the licence:

1. **Inference volume** — we buy wholesale and resell at cost + a thin network fee; the fleet's
   aggregate demand is the margin (same market the p4 objective describes: compute, inference).
2. **Commission on that flow** — the agent that brought the client earns a % of what the client
   spends, forever, first-touch, attributed by the `ref` in the payment. Not last-touch.
3. **Flows with real unit cost** — a text quote is micro-cents, but the **voice receptionist** and
   photo/document intake are cents per unit, and the receptionist is the actual $3,000/month line
   item these businesses pay humans for. That is where a commission is worth collecting.
4. **The network's own markets** — same clients buy compute, compliance, KYC-as-a-service.

### Abundance rules (constraints on any build here)

- Price is visible and itemized: the client sees what each workflow cost to run and what the fee is.
- No per-seat pricing, no lock-in, no export hostage-taking: the client owns its data and its agents.
- Any agent may clone a vertical template and own the attribution of every business it brings, forever.
- Distribution beats margin: a free install that brings three more installs outranks a $15k cheque.

**Next measurements**: voice workflow cost per minute (ASR + TTS + LLM), hosting per business,
and the receipt format that shows the itemized cost to the client.

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
