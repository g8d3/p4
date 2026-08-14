#!/usr/bin/env python3
"""E03 (Pro control) narration chunks. Written reactively after the live run.
Voice: Alnilam. One paragraph per chunk -> TTS in a single pass."""
import os

OUT = "/home/vuos/code/p4/e023-build-in-public/ag-04-pro-control/output/tts"
os.makedirs(OUT, exist_ok=True)

CHUNKS = [
    # 0 — title / question
    "I pointed fifteen AI agents at a hundred and thirty five thousand crypto "
    "candles and asked one simple question: is there a real statistical edge in "
    "here? A number, not a feeling, that survives out-of-sample testing and real "
    "trading fees. Here's the honest answer — what we found, what died, and the "
    "one thing that actually survived.",

    # 1 — setup + candle
    "Here's the setup. Twelve of the most traded perpetual contracts on "
    "Hyperliquid — Bitcoin, Ethereum, HYPE, Solana, and the rest — across four "
    "timeframes, from five minutes up to one week. In total, a hundred and "
    "thirty five thousand candles — the maximum history the exchange keeps. "
    "Before we started, I set three iron rules. Every finding had to survive "
    "out-of-sample validation, meaning it works on data it was never built on. "
    "Every finding had to survive fees. And no cherry-picking — a null result is "
    "an honest result, and we report it.",

    # 2 — fat tails
    "Finding one, and it's the foundation for everything else. Crypto returns "
    "are not a bell curve. If they were normal, a one-in-a-thousand move would "
    "be extremely rare. We measured kurtosis — a normal distribution scores "
    "three. These candles scored nine, ten, up to fourteen, on every timeframe. "
    "That means extreme moves are routine, not black swans. This single fact is "
    "why any risk model that assumes a normal distribution will eventually "
    "blow up.",

    # 3 — vol clustering
    "Finding two is the most robust result in the whole experiment. After an "
    "extreme move, volatility stays elevated — roughly double — for several "
    "candles, then decays slowly. It replicated in every single coin. But here's "
    "the catch: it predicts the size of the next move, not its direction. So you "
    "can't trade it directly. What you can do is use it to size positions — and "
    "that became the input for the volatility scaling later.",

    # 4 — nulls
    "Now the part most traders won't like. We tested everything people claim "
    "predicts direction — and almost all of it came back null. Hour of day: "
    "null. Day of month: null. VWAP distance: null. Volume change: null. Funding "
    "rates are persistent, but they carry no information about where price goes "
    "next. The weekday effect was statistically real — Monday and Wednesday "
    "down, Thursday up — but it was unstable over time, and the naive trade lost "
    "money out of sample. These are honest nulls, and they're the whole point of "
    "the channel.",

    # 5 — event study
    "Then the event study. Instead of staring at every candle, you line up the "
    "rare ones — every three-sigma daily crash — and average what happens after. "
    "The result: after a daily crash, the next five days average plus two and a "
    "half percent. It held in six out of six coins, and in both halves of the "
    "data. A real reversion signal — at the daily level only.",

    # 6 — out-of-sample
    "Here's the test that catches mirages: out-of-sample. Every threshold — what "
    "counts as a crash, what counts as low volume — is computed from the first "
    "half of history only. Then we trade the second half, which the rule has "
    "never seen. Most patterns that look brilliant on training data collapse the "
    "moment you do this. This is the single biggest reason to trust or distrust "
    "a backtest.",

    # 7 — fees + ledger
    "The second killer is fees. Every trade costs about nine hundredths of a "
    "percent round trip. That sounds tiny, but it's bigger than most statistical "
    "edges. We built a ledger of every finding — gross versus net. The five "
    "minute bounce died. The one-hour bounce died. Body-position reversion died. "
    "OBV divergence died. Almost everything that looked real on paper was smaller "
    "than the cost of the trade.",

    # 8 — combined + baseline
    "The one thing that survived — and it took fifteen agents to find it. A "
    "daily crash, or a down day on unusually low volume — either one — is "
    "followed by positive returns over the next five days. Two mostly independent "
    "signals — only four percent overlap. Pooled together: three hundred and "
    "twelve out-of-sample trades, plus zero point five five percent per trade, "
    "net of fees. Sharpe zero point four four. Meanwhile, simply being long every "
    "day over the same window lost sixty seven percent.",

    # 9 — honest limits
    "Now the honest part, because this is not a money printer. The Sharpe is "
    "modest. The drawdown reached minus thirty two percent. The twelve coins move "
    "together, so it isn't really twelve independent tests. And the entire "
    "out-of-sample window is basically one bear-market regime. These numbers may "
    "not reproduce. That's why the last piece matters the most.",

    # 10 — live monitor
    "The forward test. The strategy now runs daily against live Hyperliquid "
    "candles, as a paper-trading monitor. It reads the latest closed daily "
    "candle, checks the two triggers, and opens a five-day paper long when one "
    "fires — logging every trade net of fees, and pushing a phone notification. "
    "Right now it's holding one open paper trade — AAVE, entered yesterday. No "
    "closed trades yet. That's the honest answer: we wait, and the losses will "
    "be shown too.",

    # 11 — verdict + thanks
    "So here's the verdict. Fifteen agents. A hundred and thirty five thousand "
    "candles. Four timeframes. Fat tails are real. Volatility clustering is "
    "real. Direction is almost entirely noise. And one edge survived — daily "
    "declines mean-revert — and it's now being paper-traded live, in public. If "
    "it fails, that stays on the channel too. Thanks for watching.",
]

for i, text in enumerate(CHUNKS):
    with open(f"{OUT}/chunk_{i:02d}.txt", "w") as f:
        f.write(text)

print(f"wrote {len(CHUNKS)} chunks to {OUT}")
print(f"total words: {sum(len(c.split()) for c in CHUNKS)}")
