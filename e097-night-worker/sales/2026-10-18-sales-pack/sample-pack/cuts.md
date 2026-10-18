# Cuts — our own fleet (500 turns + 500 message samples, published as fleet/fleet-turns-2026-10-18.jsonl and fleet/fleet-history-2026-10-18.jsonl)

Ranked by measured effect on *this* loop. Every line carries its own label:
`measured` (from the run), `measured on your loop` (before/after series), or
`hypothesis` (we would run the series first).

| # | change | expected effect | confidence | effort | risk |
|---|---|---|---|---|---|
| 1 | keep the process warm | -0.37 s/turn = -26 h/year at this volume [measured boot: us, measured from outside the harness (paper 5.4; 372 ms with the startup cache warm, 940 ms cold)] | measured | low | none to correctness; watch long-lived process state |
| 2 | cut carried context from 108 KB to 30 KB [example] | -0.9 s/turn is illustrative [example]: we retracted a size coefficient (paper 8), so what you buy is the before/after series on your own loop | measured on your loop | medium | compaction can lose task state; the gate catches the wall, not the quality |
| 3 | cap tool-result size before it enters the transcript | not yet measured on this loop: we would run the series first | hypothesis | low | truncated tool output changes behaviour |

## Explicitly not recommended, with reasons

- **Cache discipline** — did not reproduce in our own data (paper §6). Measured and
  reported in `cache-report.md`; not sold as a lever.
- **Startup-scan scoping** — startup does not scale with the session store (paper §7).
- **A size coefficient** — mis-stated by 10x and would not rebuild (paper §8).

If your profile shows no lever worth pulling, the implementation half is refunded;
we would rather say that than ship a preset playbook.


## The route: what the same model costs elsewhere

Your answers price `deepseek-v4.1-flash` at $0.27/M input on DeepSeek. We measured the same base model on the routes we can reach, reading each provider's own published price (2026-10-18):

| route | $/M in | $/M cache-read | first token p50 (ours) |
|---|---|---|---|
| openrouter | $0.04 | $0.0016 | 1728 ms |
| chutes | $0.44 | $0.044 | 1148 ms |

At your volume (250,000 turns/year, 40,000 input tokens per turn, 70% cached) the input line is **$1,300/year** on your route and
**$131/year** on `openrouter` — a difference of **$1,169/year**, before any output-token difference.

**Labels, so this is not mistaken for your own bill:** the prices are the providers' own
metadata and the latency is our measurement, both on our keys and not on yours. Verify on
your account before switching, and re-run the gate after any switch — a different
deployment can behave differently even at the same model name. Re-run `routes/matrix.py`
before quoting any row: prices rotate.
