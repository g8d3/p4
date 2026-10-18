# Outreach — first touch, follow-up, close

Only for fleets that clear the bar in `roi.py --sweep` (roughly $19k/year of token
spend, or a fleet big enough that wall-clock matters). Sending this to a 3-loop
DeepSeek shop wastes their time and ours.

Rules: no attachments on first touch, no "quick call?", one number per email, and
never claim a provider/harness split we have not measured. **Send from
`focalis@agentmail.to`** (display name "Focalis audit") — never from a personal address;
replies to a prospect that wrote to hello@focalis.cc go out from the same branded inbox
(`python3 tests/mail-path.py` proves the send path). Replies land in the owner's inbox
because Cloudflare Email Routing forwards hello@, hola@ and contact@ there.

---

## Email 1 — the number (send Tue-Thu morning, local time)

**Subject:** your agents' no-op turn costs 3 seconds

We measured 65 agent turns that reply with a single word, across 3 harnesses, on one
machine: the median was 2.4 to 3.4 seconds. The model span was milliseconds.

On 500 live turns from our own fleet the split was 34% model, 29% tools and 37%
"unaccounted". We then measured that 37% properly: it is the provider round-trip (turn
start to first token), not a mystery — with that window separated, what is left
unattributed is 4 ms at the median. So the honest sentence is: about 3.2 seconds per
turn is spent waiting for the provider before the model starts writing, and the
harness's own "LLM time" field does not show it.

For a 10-loop fleet at 100 turns/day that is roughly 223 wall-hours a year spent
before any useful work happens.

We measure that per loop on your machine, in read-only mode, and then cut it. One
page of numbers first; if there is no tax worth cutting, we say so and you keep the
data.

Want the method? It is free and public: https://focalis.cc/tps/ (raw CSV, the analysis
script and the four claims we had to correct are in the same repo) — run it yourself in
ten minutes before replying. There is also a free browser preview of your own turn log,
nothing uploaded: https://focalis.cc/audit/preview/

---

## Email 2 — three days later, one artifact

**Subject:** re: your agents' no-op turn costs 3 seconds

Attaching nothing. One thing you can run in the meantime:

```
time <your-agent> -p "Reply with exactly the word PONG. Call no tools."
```

Run it five times, then five more immediately after. If the two groups differ by more
than 2x, the problem is not your model — it is cache state or dispatch, and it is
fixable without changing providers.

That is the first five minutes of our audit. The rest is doing it on every loop with
the same protocol and leaving you a regression gate.

---

## Email 3 — day 10, the honest close

**Subject:** closing the loop on agent overhead

Last note from me. If your loops are already at the floor, or your token spend is
under ~$19k/year, the audit will not pay for itself and you should not buy it —
`roi.py --sweep` in our pack says so out loud.

If either is true, two options: a single loop measured for $290, or a full fleet audit
for $1,400 with a prioritized cut list. Reply with the one word TAX and I will send
the three questions we need to start.

---

## DM variant (X, under 280 chars)

Measured: a one-word agent reply costs 2.4-3.4 s median across 3 harnesses; the model
is milliseconds. On 500 live turns the biggest slice of a turn is the provider
round-trip, which the harness log hides. We audit and cut that, read-only. Free
self-check on your own log: focalis.cc/audit/preview/

---

## What not to say

- "We will cut your costs 40%." Our own number is 20-50% off steady-state wall on
  measured loops, and it is a target with a refund attached, not a promise.
- "The LLM is free." True for no-op PONGs, false for real work (34% of wall).
- "Our benchmark shows X is faster than Y." We deliberately did not publish a
  cross-vendor ranking; n=10 per cell does not support one.
- "Your tokens are being wasted" without a number. 4.4% of turns in our sample
  produced nothing, and we could not price them — so we quote the rate, not a saving.
