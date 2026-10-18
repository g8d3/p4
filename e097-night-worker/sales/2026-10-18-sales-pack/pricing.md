# Pricing — Agent Fleet Tax Audit

All tiers are fixed-fee, prepaid 50 percent, balance on delivery of the report. No success fee, no token-based billing, no access to funds or keys ever.

## Does it pay for itself? (run `roi.py --sweep` first)

| fleet | class | token $/yr | Tier 2 payback |
|---|---|---|---|
| 10 loops x 100 turns | DeepSeek-class | $1,410 | 769 working days — **do not buy** |
| 10 loops x 100 turns | Sonnet-class | $12,600 | 90 working days |
| 10 loops x 100 turns | Opus-class | $63,000 | 18 working days |
| 100 loops x 200 turns | DeepSeek-class | $28,200 | 38 working days |

Saving assumed: 35% of the input-token line at a 70% cache hit. The audit is a
**token-cost** play only above roughly **$19k/year** of token spend. Below that we
sell the wall-clock case (a ~3 s floor per turn, 3-6x wall on a cache miss) or we
tell you not to buy. We would rather lose the deal than defend an ROI we cannot
show you.

## Tier 1 — Single-Loop Measure — 290 USD

For one agent loop that feels slow.

- Instrument 1 loop for up to 3 days
- 50+ no-op and live turns measured: wall, model span, unaccounted span, input and cached tokens
- 1 breakdown page: where the ~2 to 3 s go in your loop
- Turn-budget formula with your numbers
- 30-min readout call
- Delivery: 5 business days from access

## Tier 2 — Fleet Audit — 1,400 USD

For teams running 3 to 10 agents. Most popular.

- Everything in Tier 1, for up to 5 loops
- Cache measured and reported (hit rate, cached tokens per turn, wall at fixed input) — reported, not prescribed: it did not separate fast from slow turns in our own data (paper §6)
- Transcript-size curve for your loops, measured as ranges. When to compact: our default is a
  ~100 KB heuristic and we label it as that — we tried to fit a size coefficient of our own and it
  did not reproduce (paper §8), so we measure your curve and you set the threshold
- Prioritized cut list with expected seconds and token savings per fix
- **The route is priced, not assumed.** If the same model is cheaper, or answers faster, on another
  route you already have access to, the cut list says so with the numbers — measured on our own
  keys and published at <https://focalis.cc/audit/routes/> (one model's input price runs 22.1x
  between routes — $0.0199/M on one against $0.44/M on another, both from the providers' own
  metadata on 2026-10-18; on another the cheap route is 6.0x slower to first token; and on a third a
  **1.4% price difference came with a 7.7x latency difference** — 14.8 s against 1.9 s to first
  token for the same model name). The same holds for the closed models: `claude-opus-5` costs
  `$5/$25` per million on **both** of the routes we could price and answers in **2.19 s** on one
  against **1.25 s** on the other (**1.75x**) — the route is the unit even when the list price is
  identical. OpenAI's models are in the table too (`gpt-5.4`, `gpt-4o`), and they are the cleanest
  case: both routes charge the identical list price and the first token still takes **1.54x** and
  **1.53x** longer on one of them. When every route charges the same list price we say that
  instead, and the finding is the latency.
- Regression check script you keep (fails CI if steady-state wall regresses)
- 60-min readout + 30-day follow-up questions by message
- Delivery: 10 business days from access

## Tier 3 — Fleet Audit + Cut — 3,900 USD

We measure, then we implement the cuts with you.

- Everything in Tier 2, for up to 12 loops
- Implementation of the cuts **your** profile shows, behind your code review. We do not arrive with a preset list: cache discipline, startup-scan scoping and a size slope all failed to reproduce in our own data (paper sections 6-8), so we will not sell them. The one we have measured as real and removable is per-invocation boot (372 ms per turn if your loop spawns a process per turn, 940 ms on a cold cache — measured, with both raw runs published); beyond that, whatever your numbers show
- Before/after proof: same 50-turn protocol re-run, wall and token deltas signed off
- Reference target: 20 to 50 percent off steady-state wall on measured loops, or the implementation half is refunded. If your profile shows no lever worth pulling, we tell you before you pay the implementation half
- 90-day regression window: if the tax creeps back, we re-diagnose once free
- Delivery: 20 business days from access

## Retainer — Fleet Tax Monitoring — 490 USD/month

For teams that already had an audit (or run our monitor) and do not want the tax to
creep back. This is the recurring product: the audit is the diagnosis, this is the
watch. Cancel any month.

- Continuous per-turn telemetry from your loops (our monitor writes it to the
  workspace; a supervisor reads it, no agent access needed)
- Monthly one-page report: wall floor per loop, cache-hit rate, share of turns that
  failed or produced nothing, spend by session, context pressure against each window
- Alerts two ways: the regression gate you kept fires at **+20% wall or 5% wasted turns**
  (we maintain it), and we flag the floor, the cache-hit rate or the wasted share moving more
  than **20%** against the audited baseline
- Quarterly re-measurement with the same 50-turn protocol, plus maintenance of the
  regression script you kept
- One standing 30-min slot per month, or by message

Why it is priced monthly and not per token: nothing we sell is billed on your usage.
A retainer is worth it exactly when the monthly saving or the avoided regression
exceeds 490 USD — check it with `roi.py` before you buy. If your fleet is below the
threshold, we will say so.

## Rules common to all tiers

- Read-only instrumentation first. Write access only in Tier 3, only to agreed files, only with review.
- We never touch secrets, wallets, customer data, or production keys. You redact before we read.
- Extra loop beyond tier: 180 USD each (Tier 2/3 only).
- Rush (half the delivery time): plus 40 percent, subject to slot.
- Payment: transfer or stablecoin invoice; work starts on first payment clearing.
