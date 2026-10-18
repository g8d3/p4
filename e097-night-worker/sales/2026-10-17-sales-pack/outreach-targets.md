# Outreach targets — real threads, verified live, with the reply already written

Written 2026-10-17 20:1xZ by the night worker (relay 01a14b71). Purpose: give the human a
list where a **single substantive reply** reaches people who have *already* said, in
public, that this is their problem. No unsolicited mass-mailing; no link-dropping.

How the list was built (so it can be re-run):

- questions and candidate threads: `python3` + Tavily (`/tmp/night/r13/tavily.json`,
  8 queries, 64 rows) — Tavily cannot fetch Reddit, so Reddit rows are index-only.
- **verified live**: HN's own API (`https://hacker-news.firebaseio.com/v0/item/<id>.json`
  and `https://hn.algolia.com/api/v1/search_by_date`) gives title, date, points and
  comment count. Every HN row below was fetched at 20:1xZ, not copied from a search
  snippet. Reddit rows are marked `unverified`.
- freshness was checked deliberately: a reply on a 12-month-old thread reaches nobody, so
  every HN row here is **< 90 days old** unless marked otherwise.

Rule for using these (from `DISTRIBUTION.md`, unchanged): answer with the measurement, do
not pitch in the thread; the paper's last section carries the offer, and the disclosure
line below says so in one clause. Do not post the same text twice — HN notices.

## The two that are worth 5 minutes each

### 1. HN — "Why harnesses matter for energy (and token) efficiency" · 2026-10-16 · 55 pts · 26 comments

<https://news.ycombinator.com/item?id=50124642> · post: <https://neuralwatt.com/news/why-harnesses-matter-for-energy-efficiency>
Author is `ccgibson`, CEO of Neuralwatt (inference cloud billed on measured GPU energy).
The thread's premise — *the harness, not only the model, decides how much prefill work is
wasted; uncached input 1.6%→11.1% across clients* — is our thesis from the wall-clock
side. **Still collecting comments today.**

Reply (post as a top-level comment; everything in it is from our own published data):

> We measured the same thing from the other end — wall clock instead of energy — by
> timestamping the process's NDJSON stream from outside the harness. One-word turn, 5
> reps: **372 ms of process boot** before the first event (940 ms on a cold cache), **1554 ms** from turn start to
> the provider's first message (median, 1193-1605 across reps), then **2 ms** of actual
> model output. Two things follow that I think matter for this thread:
>
> (a) that roundtrip lands *before* the clock most harnesses report as "LLM time", so
> harness-level logs understate it by three orders of magnitude on a one-word reply;
> (b) switching models barely moves the floor. On our own fleet's 500 live turns the
> unaccounted per-turn span has a p50 of 1.5-2.5 s across three different providers while
> the model span's p50 ranges from 1 ms to 9.1 s. A model-switching strategy addresses
> the model slice, not the floor.
>
> One negative result that may be useful here, since cache rate is the thread's topic: we
> expected cache state to predict wall time and it did not separate our runs — 9216 cached
> input appears in a 16.6 s turn and in two ~3 s turns, and four of ten runs in that cell
> were 2-6x slower in one contiguous streak that then recovered. We could not name the
> cause, so it is reported as unexplained, not as a cache effect. If an energy-side series
> shows the same failure to separate, that comparison seems worth having.
>
> Method, raw CSV, script, and the three mechanisms we retracted along the way:
> https://focalis.cc/tps/ — disclosure, since HN expects it: that page ends with a paid
> audit offer.

### 2. HN — "Launch HN: Tokenless (YC S26) – Automatic model switching to save money" · 2026-07-29 · 71 pts · 63 comments

<https://news.ycombinator.com/item?id=49099143> — the founder is in the thread answering
everyone. Directly on our measurement: what model switching can and cannot buy.

Reply:

> Genuine question about the model of the saving, because we measured the thing model
> switching does not move. From outside the harness, one-word turn: 372 ms process boot (940 ms cold) +
> 1451 ms turn-start→provider-first-message + 2 ms model output. On our own fleet's 500
> live turns, wall per turn is 8.7 s, split 34% model / 29% tools / 37% unaccounted. That
> last slice is the one we later measured properly: it is the provider round-trip (turn
> start to first token), and its p50 sits at 1.5-2.5 s across three providers while the
> model slice's p50 ranges 1 ms→9.1 s — so a switching strategy moves neither of the two
> largest slices. So a switching strategy is chasing the 34% slice, and on
> a cheap model the token line it optimises is often already smaller than the wall cost of
> the same turns — we published a calculator that says "no, do not buy our audit" for
> exactly that case (https://focalis.cc/audit/, the currency is wall-hours, not tokens).
> Do you see the floor move at all when you switch, or is the win purely in the per-token
> price?

## The rest of the verified list (a reply each, if the topic is still warm)

| # | thread | when | why it fits | the one-line opener to use |
|---|---|---|---|---|
| 3 | [Show HN: I Cut my Agent Tokens By 50%](https://news.ycombinator.com/item?id=50047627) | 2026-10-11 · 6 pts · 6 c | a token cut is not a wall cut, and we retracted three of our own cuts | "Nice result — do you have the p50/p90 wall per turn before and after? We tried three context cuts of our own and retracted all three (cache discipline, startup scan, a size coefficient); the token number moved while wall barely did." |
| 4 | [Local Indexing to reduce tool calling and token usage](https://news.ycombinator.com/item?id=50049508) | 2026-10-12 · 127 pts · 52 c | tools are 29% of fleet wall, so this *should* show up in wall | "Tools are 29% of the wall we measure (34% model, and a 37% the harness calls "unaccounted" which we later measured as the provider round-trip) — if your index removes tool calls, that should be visible as seconds, not just tokens. What does per-turn wall look like before/after?" |
| 5 | [Managing AI Coding Costs at Scale](https://news.ycombinator.com/item?id=49214468) (Databricks) | 2026-08-07 · 317 pts · 268 c | the cost-control thread; our calculator is the free honest answer | "For anyone forecasting from this: we published the calculator we use (open, runs in the browser) — it says 'we would say no' when the token line is too small for the audit to pay for itself, which for a 10-loop DeepSeek fleet is the honest answer." |
| 6 | [Ask HN: How are people forecasting AI API costs for agent workflows?](https://news.ycombinator.com/item?id=47332177) | 2026-03-11 · 5 pts · 22 c | the question is literally our product | "Two numbers we found worth putting in a forecast: a per-turn floor that is not the model (372 ms boot warm, 940 ms cold + 1554 ms pre-response on a one-word turn) and the tail (p90 unaccounted 4.6 s, worst 85 s) — the tail is what makes the monthly number wrong." |
| 7 | [Launch HN: Agent37 (YC F26) – Low-cost agent sandboxes](https://news.ycombinator.com/item?id=50059096) | 2026-10-12 · 162 pts · 128 c | a sandbox that boots per turn pays exactly our measured boot | "Question about the cost model: does the sandbox boot land inside the per-turn budget? We measured 372 ms of process boot per turn on our own loop (940 ms on a cold cache, because two catalog fetches happen at startup), which at 10 loops x 100 turns/day is 26 wall-hours/year before any model call." |
| 8 | [Show HN: Frugal Tokens — explore costs and usage across coding agents](https://news.ycombinator.com/item?id=49364223) | 2026-08-19 · 37 pts · 10 c | same-shelf tool, missing the column we measure | "The missing column for us was pre-response (turn start → provider's first message): 1451 ms median on a one-word turn, and it does not appear in any harness log we tried. If you ever add it, the two projects would cover the whole turn." |
| 9 | [Show HN: Oodle.ai – $10 per million agent traces](https://news.ycombinator.com/item?id=48907615) | 2026-07-14 · 31 pts · 12 c | observability vendor at 1/1000th our price → complementary, not competing | "At this price the interesting question is what a trace should carry: we ended up needing turn-start→first-token (our pre-response, median 1451 ms) because the harness's own 'LLM duration' measures only the stream." |
| 10 | r/LLMDevs — [Who's using agents with APIs? The costs are insane!!](https://www.reddit.com/r/LLMDevs/comments/1webjcw/whos_using_agents_with_apis_the_costs_are_insane) | `unverified` (Reddit blocks our fetcher: 403; content came from Tavily's index) | the OP asks exactly the question we answer with data | see the HN comment above; strip the HN framing and lead with the number that answers *their* question. Verify the thread is still alive before posting. |
| 11 | r/LLMDevs — [Fast at what? Measuring inference speed beyond the first token](https://www.reddit.com/r/LLMDevs/comments/1x6me2j/fast_at_what_measuring_inference_speed_beyond_the) | `unverified` | TTFT vs throughput vs "agent finished" — our §5 is about exactly the clock that lies | "The clock that lies the most is the harness's own: on a one-word reply it reports 2 ms because it starts its timer after the response has already arrived. The real roundtrip was 1451 ms." |

## Direct email — the two recipients worth a cold mail

No public address found for either (checked their sites' obvious paths); these are for the
human's own address, **not** the agent inbox:

1. **Neuralwatt** (`ccgibson`, CEO) — wrote today's harness-energy post; runs an inference
   cloud that bills on measured energy. A one-paragraph mail with our wall-clock
   decomposition is a plausible *data-sharing* conversation, not a pitch: they have energy
   numbers we don't, we have per-turn wall numbers on real fleets. Contact form/site
   `neuralwatt.com/about`. **No address published → the HN reply above is the way in.**
2. **Databricks** (author of *Managing AI Coding Costs at Scale*, 317 pts) — enterprise
   cost-control audience; the honest angle is the free calculator + our retractions, not
   the audit. Requires guessing a contact; not worth blind-guessing an address.

## The 5-minute playbook (what to do when you wake up)

1. Post reply **#1** as-is (the thread is live today; HN allows one comment per thread).
2. Post reply **#2** only if you want a second HN interaction in the same hour — new
   accounts get rate-limited; if both, do #1 first and wait.
3. Nothing else needs doing: #3-#9 are a menu, not a queue, and the offer page is already
   public and linked from the paper's last section.

## What NOT to do

- Do not post from `@novaisabuilder` (3 followers, Solana-memecoin bio — see
  `DISTRIBUTION.md`).
- Do not send the same paragraph to several HN threads; pick the thread where the number
  answers the actual question.
- Do not claim the *cache* result as a finding — it is a retraction (§6). The only claim
  we can make about cache is that it did not separate our runs.
- Do not post a link without the disclosure clause; on HN an undisclosed vendor link is
  the whole ballgame.
