# Self-check: measure your own agent tax in about 10 minutes

Free. You do not need us, a contract, or to send us anything. If it turns up nothing,
you have lost ten minutes. If it turns up something, you will know roughly how much
before anyone quotes you a price.

You need: shell access to one loop, the ability to run it non-interactively, and
read access to wherever it stores session transcripts.

## 1. The no-op floor (3 minutes)

Run this five times, one after another, in the workspace your loop normally runs in:

```bash
time <your-agent-command> -p "Reply with exactly the word PONG. Call no tools."
```

Note the five wall times. Now run it again immediately (`--continue` or equivalent)
and note the times.

**Read it as:** the floor. A reply of three tokens that takes 2-4 seconds is not the
model. Do not average the numbers into a single figure — the spread is the finding:
if one run is 3 s and the next is 15 s, you have a cache or dispatch problem, not a
model problem.

## 2. Where the time went (2 minutes)

If your harness logs spans (ours does: `.pi-web/tps-turns.jsonl`), drop that file into the free
preview at **https://focalis.cc/audit/preview/** and it does steps 2-4 in the browser (nothing
uploaded; CSV from another harness works too). Otherwise, find the row for
each run and compare `turnMsTotal` with `llmDurationMs` and `toolMsTotal`.

```
unaccounted = turnMsTotal - llmDurationMs - toolMsTotal
```

**Read it as:** harness + provider time before the model starts streaming. Do not
call it "harness overhead" — an external measurement cannot split harness from
provider. What you *can* say: the model span is small, the rest is large.

## 3. Does size matter? (3 minutes)

Compare a session with a small transcript and one with a large one (100 KB vs 1 MB of
session JSONL). Same no-op prompt, five runs each.

**Read it as:** if the large one is several times slower, the transcript is in your
per-turn path and compaction is your lever. If both are the same, your harness is
reloading from a snapshot and size is not the problem.

## 4. Cache state (2 minutes)

From the same rows, compare wall time between runs where the provider reports cached
input tokens and runs where it reports zero (or a tiny number), at *identical* input
token counts.

**Read it as:** in our own sample this test **failed to explain anything** — the same
cached-token count appeared in a 16.6 s run and in two ~3 s runs. Run it anyway: if your
numbers *do* separate cleanly, that is your lever; if they do not, do not buy a cache
story from anyone, including us (paper §6).

## 5. Write down four numbers

1. Floor wall per turn (median of your no-ops, with the spread).
2. Unaccounted seconds per turn on real work.
3. Your cache-hit rate.
4. Share of turns that fail, abort, or produce nothing.

Multiply (1) or (2) by your turns per day. That is your tax, in wall-hours.

## What we would do that you just did not

- Run it on **all** your loops, not one, with the same protocol, on the same day.
- Instrument **inside** the loop to split provider latency from harness work — the
  split you cannot see from outside (our own paper says so, see §5).
- Turn the result into a **prioritized cut list** with seconds and dollars per item.
- Leave you a **regression script** so the tax cannot quietly creep back.

That is the audit. If step 5 says your tax is small, do not buy it — `roi.py --sweep`
in this pack will tell you the same thing in one command.
