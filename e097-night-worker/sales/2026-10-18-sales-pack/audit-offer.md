# Audit Offer — Scope and Deliverables

## Scope

In scope:

- Where one turn goes, measured from outside the harness: **boot** (process start → first event), **pre-response** (turn start → assistant message start), **stream** (first token → end), and **tools**. We report pre-response as a bound and do not split it into dispatch vs provider, because nothing exposed outside the harness separates them (paper §5.4).
- **Boot removability**: whether your loop pays the measured 372 ms per turn (940 ms cold) for a process it could keep warm.
- Transcript-size cost *as measured on your loops*, reported as ranges. We do not fit a coefficient: ours was mis-stated and did not reproduce (paper §8).
- Cache behavior *measured and reported* (hit rate, cached tokens per turn, wall at fixed input). It is not sold as a lever: it did not separate fast from slow runs in our data (paper §6).
- The slow-turn tail: p50/p90/worst, with the cause named only when we can measure it.
- Wasted turns: share that failed, aborted or produced nothing, with priced and unpriced counted apart.
- Per-turn budget: boot + floor + expected provider + input tokens x price, fitted to your numbers.
- Cut recommendations ranked by measured seconds per turn and token re-spend avoided, each labelled measured or hypothesis.

Out of scope (we do not do these):

- Model quality, prompts, or strategy logic changes beyond compact policy.
- Production secrets, API keys, wallet keys, customer data — we never ask, never accept, never store.
- Moving funds, signing transactions, touching production deploys directly.
- Sub-second guarantees or cross-vendor benchmark claims. Our reference numbers are single-machine, small-n, same as the paper says.

Access we need:

- Read-only logs or a staging clone of each loop in scope.
- The exact command that runs one turn, and permission to run 50+ no-op turns (`Reply with exactly the word PONG. Call no tools.`) plus normal live turns.
- Dependency and session-store sizes (directory listing with sizes, not contents).

Access we refuse:

- Plaintext secrets of any kind. Redact before sharing; we stop the clock if secrets appear and resume after you rotate them.

## Method (same protocol as our paper)

1. Baseline: 50-turn no-op series per loop, wall measured **outside** the harness (boot, pre-response, stream, tools, in tokens, cached tokens).
2. Size series: overhead vs transcript KB on your real transcripts, reported as ranges over the sizes your loops actually reach.
3. Cache series: wall vs cached-token state at fixed input, reported as measured (we found no separating effect in our own data — paper §6 — so it is reported, not prescribed).
4. Boot profile: process per turn vs warm process, boot cost measured per invocation.
5. Money mapping: turns x (boot + floor + context x price) at your provider rates — priced per
   route, not per model name: the same model is not the same price, or the same first-token
   latency, on every route, so we ask which route serves each loop and use that number (our own
   measurements are public at <https://focalis.cc/audit/routes/>).

Sample sizes and caveats from our own study carry over: n=50 per loop, jitter is ~1 s run-to-run, providers differ across harnesses, single samples are labeled anecdotes not rates.

## Deliverables

1. `breakdown.md` — one page per loop, in the shape of `deliverable-template.md`: boot / pre-response / stream / tools with the method for each, the tail (p50, p90, worst), and wasted turns with priced and unpriced counted apart.
2. `size-curve.md` — overhead vs transcript KB on your loops, reported as ranges over the sizes you actually reach (we do not fit a coefficient; ours did not reproduce).
3. `cache-report.md` — hit rate and cached tokens per turn as measured, with wall at fixed input. If it does not separate your fast from slow turns, the report says so (ours did not).
4. `cuts.md` — ranked fixes with expected savings, effort, risk, and a measured/hypothesis label per line. Tier 3 adds before/after proof. Cache discipline, startup-scan scoping and size coefficients are listed as *not recommended* with the reason.
5. `budget.md` — your turn-budget formula with numbers, plus the regression check script (Tier 2+).
6. Raw data — CSV with the same columns as our paper (`harness,run,wall_s,llm_ms,total_ms,unacc_ms,in_tok,cache_tok,out_tok,notes`) plus per-run logs.

## Acceptance

- Numbers reproducible from the delivered CSV + logs by re-running the documented commands.
- Tier 3 cut target met on the re-run protocol, or the implementation half is refunded.
- 48-hour client veto on any public mention. No logo, no numbers, no name leaves your repo without written approval.
