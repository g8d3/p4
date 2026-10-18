# Agent Fleet Tax Audit — We Measure It, Then We Lower It

**What this is:** a paid checkup for teams running AI agents. Some of the money your agents spend is waste — retries, the expensive route, turns that produce nothing. We measure that waste on *your* loops, then we remove it. One-line version: 1,000 answers a day with 1¢ wasted on each is $3,650 a year thrown away — we find that cent and cut it. If your numbers say the audit doesn't pay, we tell you so before you pay us.

Your agents are slow and expensive even when they do nothing. We prove it with numbers, then we fix it.

## The finding (65 runs, 3 harnesses, one night)

- A no-op turn — reply with exactly one word, call no tools — costs **2.4 to 3.4 s median** on every harness tested.
- **We measured where the time is, from outside the harness.** A one-word turn: **372 ms** of process boot (940 ms on a cold cache — see below), then **1554 ms** before the provider's response arrives (1224-1748 ms across reps), then **3 ms** of model output. The roundtrip lands *before* the clock the harness itself reports, which is why tools that read the harness log tell you the model took 3 ms. We cannot split that 1554 ms into dispatch vs provider — nobody outside can — and we say so rather than guess.
- **We found and removed part of our own tax, and published both numbers.** The boot first measured 929 ms; two model-catalog fetches an extension runs at startup were inside it, so they are cached for six hours now and the same command on the same machine measures **372 ms warm / 940 ms cold** (raw runs and the reproducer are in the paper's repository). We quote the pair because the lever is 2.5x smaller than the number we used to sell.
- Transcript size costs something, but we cannot give you a coefficient: our prior series (n=8) shows ~1 s at 30-108 KB, 1.5-1.7 s at 170-228 KB and ~5 s at megabyte scale, and when we tried to rebuild that ladder to fit a slope, the big ingests did not stick (paper section 8). We measure your curve, per loop, at the sizes your loops actually reach.
- **Cache state did NOT predict wall time in our sample — we checked, and we say so.** We expected the same 9.4k input to be fast on a cache hit and slow on a miss. Grouping the runs by cached tokens does not separate them: 9216 cached appears in a 16.6 s run and in two ~3 s runs. Four of ten runs in that cell were 2-6x slower with no measured signature, in a contiguous streak that then recovered. We report that as unexplained, not as a cache finding.
- **Rates from short replies are easy to fake and we do not use them.** A one-word reply is often delivered in a single chunk, which collapses any window you divide tokens by; we guard that in our own tool rather than quote the number.
- Fleet math: **1,000 no-op turns burn ~52 minutes of pure overhead.** 10 loops x 100 turns a day = ~52 minutes a day of it, before any useful work happens — and ~4.5 wall-hours a day on real work (the published window's mean is 16.3 s/turn).
- **On real work it holds up, and you cannot buy your way out of it.** The window we publish ([fleet/](https://github.com/g8d3/transcript-tax/tree/master/fleet), 500 turns, one machine, 15:16–20:40Z on 2026-10-17): **median 7.2 s wall per turn, mean 16.3 s — 25% model, 23% tools, 52% the provider round-trip**, which the older harness log called “unaccounted” ([paper §9](https://focalis.cc/tps/article.html) has the two methods side by side and both are recomputable with the published exporter). Per model, the round-trip floor barely moves (p50 1.5-2.5 s) while the model slice's p50 ranges from 1 ms to 9.1 s: switching models changes the model slice, not the tax.
- **The tail is worse than the median.** On the published window the p90 turn is 29.3 s of wall and the worst turn is 300 s — five minutes on one turn. At fleet scale you meet that tail often.
- **3.2% of our turns produced nothing** (failed, aborted, empty — 16 of 500 in the published window: 15 errors, 1 aborted). We do not quote a dollar figure for that waste: every one of those errors ran on a model with no public list price, so the honest number is the rate, not a cost.

Source: working paper `Transcript Tax 2026` (65 runs, spend ~8 cents, methods and caveats inline). We show you the raw CSV, the per-run logs, and the breakdown before we sell you anything.

**We ship the instrument, not just the report.** The monitor we audit with is open and runs in your own workspace: every turn row carries `preResponseMs` — turn start to the provider's first token — beside the model span, as a `Pre` field in the turn rows and in `/tps turns`. It also flags the turns that burn budget and produce nothing, and it will not print a fabricated rate for a one-word reply (a collapsed window reads as "–", never as a number). You keep the tool after we leave. (Verified on our own machine: the panel serves the exact build that carries the column, byte-identical hash, and the live turn rows have been recording `preResponseMs` since we fixed the deployment.)

## What we do

A read-only audit of your agent fleet. It is a measurement service: we have retracted
three of our own mechanisms (paper sections 6-8), so what we sell is the instrumented
number on your loops and a cut list derived from *your* profile, not a preset playbook.

1. **Measure** — instrument your loops with per-turn wall, model span, pre-response span, unaccounted span, input tokens, cached tokens. You can run the first half of that yourself, on your own log, in the browser (nothing is uploaded): **[https://focalis.cc/audit/preview/](https://focalis.cc/audit/preview/)**.
2. **Locate the tax** — boot, pre-response, stream and tools per turn, measured from outside the harness; the token re-spend of carried context; the slow-turn tail; and the share of turns that burn budget and produce nothing. We report pre-response as a bound and do not pretend to split it into dispatch vs provider: the provider's own stream events fire with the response, so nothing outside the loop separates them.
3. **Cut it** — the one lever we have measured as real and removable is boot: 372 ms of every turn if your loop spawns a process per turn, zero if it keeps one warm. For a 10-loop fleet that is 26 wall-hours a year, gone (65 if every turn paid the cold fetch). Beyond that, the cuts come from your own profile (context carried per turn, the slow-turn tail). We do not sell cache discipline, startup-scan scoping or a size slope: all three failed to reproduce in our data (paper sections 6, 7 and 8).
4. **Lock it in** — per-turn budget formula and a regression check you keep running after we leave.

No rewrites. No new vendor. No access to customer funds, keys, or production secrets. Read-only first, changes behind your review.

## Who it is for

- Teams running 5+ agents (support, trading, research, ops) where latency compounds.
- **Fleets whose annual token line is large** — from our own sweep, the audit pays for itself inside a quarter once token spend clears roughly **$19k/year** (35% input cut). At Opus-class prices that is a 10-loop fleet; at Sonnet-class, ~30 loops.
- **Cheap-model fleets still pay the wall tax, not the token tax.** A 10-loop DeepSeek fleet spends ~$1.4k/year in tokens — we will not sell that fleet a token saving. It still burns ~208 wall-hours/year at a 3 s floor, and a cache miss costs 3-6x wall at identical tokens. For those, we price against operator time and loop capacity, or we say no.
- Anyone whose agent bill scales with turns x context and nobody can explain the line item.

Run `roi.py --sweep` yourself before you talk to us; if it says no, we will too.

## Read the numbers first

The full paper — methods, the 65-run dataset, the three mechanisms we retracted, and
our own fleet's 500 live turns — is public, with the raw CSV and the analysis script:

- Paper: **[https://focalis.cc/tps/](https://focalis.cc/tps/)** — same text, no tracking of its own, no external requests (the hosted copy gets Cloudflare's cookieless page-view beacon).
- Repo (code + `bench.csv` + figures, MIT / CC BY 4.0): **[https://github.com/g8d3/transcript-tax](https://github.com/g8d3/transcript-tax)**
- Our own **claims audit** of this page — every number, its source, and every
  correction we made to it (including what we retracted): **[https://github.com/g8d3/transcript-tax/blob/master/CLAIMS.md](https://github.com/g8d3/transcript-tax/blob/master/CLAIMS.md)**
- **Where the token enters changes what it costs.** The same model across several providers, measured: price, first-token latency and total, with the routes that exist but cannot answer: **[https://focalis.cc/audit/routes/](https://focalis.cc/audit/routes/)**

If the numbers do not survive your reading, tell us and we drop the pitch.

## Who we are

Focalis S.A.S. — a small software studio in Bogotá, Colombia (UTC-5). We run our own
agent fleet, which is where the 500-turn dataset in the paper comes from, and we built the
instrument we measure it with. We sell the measurement, and only the measurement.

## Next step

Pick a tier in the pricing table above. The audit starts with one loop, one day, one breakdown page. If the numbers do not show a tax worth cutting, you pay the base fee and keep the data.

See the shape of that breakdown page before you buy — a blank template filled with one labelled example loop, no client data in it: **[https://focalis.cc/audit/sample/](https://focalis.cc/audit/sample/)**

The three questions we ask every prospect, what to attach and what you get, are public:
**[https://focalis.cc/audit/intake/](https://focalis.cc/audit/intake/)**. Write to
**hello@focalis.cc** with the word `TAX` in the subject — the three questions we send are
exactly the ones published there.

Focalis S.A.S. (Bogotá, Colombia) is the seller. Fixed fee, prepaid 50% and balance on
delivery. Card checkout is not live yet — the merchant-of-record application is in
progress — so today we invoice directly: bank transfer or stablecoin, and work starts
when the first payment clears. When card checkout goes live it will be collected by the
merchant of record, which handles tax and issues the receipt, and we never see or store
card details. Terms, privacy and refunds are published at
**[https://focalis.cc/terms](https://focalis.cc/terms)**,
**[https://focalis.cc/privacy](https://focalis.cc/privacy)** and
**[https://focalis.cc/refunds](https://focalis.cc/refunds)**.

No promises of sub-second miracles. Just the tax, measured, then lowered.
