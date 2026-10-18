# Objections and the honest answers

Answers we can defend with our own measurements. Where we cannot, we say so — a
prospect who catches us overclaiming costs more than the deal.

## "Our tokens are cheap, so there is nothing to save"

Usually true, and it decides the sale. Run `python3 roi.py --sweep` before the call:

| fleet | class | token $/yr | audit payback |
|---|---|---|---|
| 10 loops x 100 turns | DeepSeek-class | $1,410 | 769 working days — **no** |
| 10 loops x 100 turns | Sonnet-class | $12,600 | 90 working days |
| 10 loops x 100 turns | Opus-class | $63,000 | 18 working days |
| 100 loops x 200 turns | DeepSeek-class | $28,200 | 38 working days |

Rule: the audit is a **token-cost** play only above roughly **$19k/yr** of token
spend (35% input cut, 70% cache hit, Tier 2 fee). Below that, either sell the
wall-clock case below, or do not sell. Do not invent a token saving for a
$1.4k/yr fleet.

The wall tax survives cheap tokens: our measured floor is ~3 s per no-op turn
regardless of price, and four of ten runs in one cell came in 2–6x slower than the
rest at identical input tokens with no signature we can name (we checked the cache
column; it does not explain them). 10 loops x 100 turns = 208 wall-hours/year of
pure overhead, and the operator still pays for that in attention, in latency, and
in how many loops one machine can run.

Price those hours and the same cheap fleet pays back: `roi.py --agents 10 --turns 100
--hourly 50` gives 312 wall-hours/year (208 floor + 104 cache-miss) and a payback of
**98 working days**. That is the honest pitch for a cheap-model fleet — time, not
tokens. If you cannot price the hours, do not sell it.

## "We can measure this ourselves — your protocol is public"

Yes, and that is the point: the protocol (50 no-op turns, size series, cache
series) is in the paper, and `roi.py` is free. What you are buying is (a) the
instrumented run on *your* loops, (b) the provider-vs-harness split, which our
own paper says we cannot do from the outside, (c) the prioritized cut list with
seconds and dollars per item, and (d) the regression script that keeps the cut
from creeping back. Self-measurement usually stops at "it feels slow".

## "We are on a flat-rate subscription, so tokens are free"

Then the token line is not the argument and we should not pretend otherwise.
What still applies: the wall floor, cache-miss wall penalty, context pressure
against the provider's window, and the share of turns that burn budget and
produce nothing (failed, aborted, empty). Price the audit against operator time
and loop capacity, not against tokens.

## "How do we verify you actually cut anything?"

Every tier re-runs the *same* 50-turn protocol after the change and reports wall
and token deltas side by side, on your machine, with the script in your repo. Tier
3's implementation half is refunded if the measured steady-state wall does not
move. You are not asked to trust a before/after we computed elsewhere.

## "Isn't this just a benchmark paper?"

The paper is the evidence, not the product. The product is a measurement on your
loops plus a regression gate you keep. We deliberately did *not* publish a
cross-vendor ranking: our own caveats (n=10 pongs per cell, provider routing
differs per harness, one machine) do not support one.

## "Your own report says the LLM is free. That sounds wrong."

It was partly an artifact and we corrected it before publishing (report §5): the
LLM span is measured from the harness's own start event, which can fire at the
first streamed chunk, so provider time before that lands in "unaccounted". What
we stand behind: the measured wall floor per turn, the cache-miss wall penalty,
and the token re-spend of context. What we refuse to claim: a clean
provider/harness split. That split is Tier 2 instrumentation work, which is
exactly what makes it worth paying for.

## "We already compact aggressively"

Then prove it in the measurement. In our own dataset a harness compacted 103k
tokens down to 9.4k and then *grew back*; another ingest that was supposed to pin
2 MB cached only 7.7k — less than the 100 KB case. Compaction policies that look
right in config often do not stick per turn. We measure cached tokens per turn
rather than trusting the setting.

## "Why not just switch to a cheaper model?"

That is a quality trade, and it is yours to make. It also does not remove the
wall floor, and it can make cache economics worse if the new provider's prefix
caching behaves differently. We measure before recommending either.

## "We cannot give a stranger access to our agent stack"

Nor should you. Tiers 1 and 2 are read-only: logs, a staging clone, the exact
command that runs one turn. No secrets — redact first; if secrets appear we stop
the clock and resume after you rotate. We never take keys, wallets, customer
data, or production deploys. Write access exists only in Tier 3, only to agreed
files, only behind your code review. If your process needs a signed NDA before a
log leaves the building, we sign yours (or you redact first and skip it).

## "The fee is high for a report"

Compare it to the annual line it touches, not to a document: $1,400 against a
$12,600/yr token bill is 11% of one year, and it buys the split and the cut list
that keep applying after we leave. If the sweep says your fleet does not clear
the bar, we will say so and sell you the $290 single-loop measurement or nothing
at all.

## "You publish the instrument and the gate — why would I pay for the audit?"

Because you already have the tool and still cannot act on it: the monitor tells you what one
turn cost, not which slice of it is removable. Concretely, on the window we publish
([fleet/](https://github.com/g8d3/transcript-tax/tree/master/fleet), 500 turns) the panel shows a
median of 7.2 s per turn (mean 16.3 s) and 3.2% wasted turns; the audit is what turned that into "the provider
roundtrip is 52% and the residual is 4 ms at p50" and then into a ranked cut list. The gate is
worthless without a baseline that was taken *after* a change you trust, which is the part the
audit produces. If you would rather do that work yourself, do it — the tool, the paper and the
calculator are all public, and that is on purpose: it is the only honest way to sell
measurement.

## "Your example pages are your own data. Where is the case study?"

There is no case study yet, and we will not publish one with invented numbers. What we publish
instead is everything that does not need a client: our own window (`fleet/` in the repo, raw),
the filled example deliverables (`/audit/sample/`), the claims audit of our own copy, and the
retractions. The first real client gets a before/after with their numbers, and only with their
written approval — the 48-hour veto in the terms is not decoration.

## "I have no turn log. Do I still have an audit?"

Yes, but it starts one step earlier: the monitor is free and takes an afternoon to have writing
rows, or you send a day of logs from whatever harness you already run and we write the adapter
(that is in scope, not an extra). The browser preview at `/audit/preview/` reads our format
directly and any CSV you map by column, so you can see the shape of the answer before you pay.
What we will not do is audit from a description: without rows, all we would have is an opinion.
