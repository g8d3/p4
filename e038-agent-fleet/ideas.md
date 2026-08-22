# Fleet ideas: collaborative pipelines for 5 agents

Constraint honored everywhere: **API > browser**. Browser automation is fragile and
captchas block scraping, so every idea below runs on clean APIs (Hyperliquid,
YouTube Data API, GitHub/Algora APIs) or fully local rendering. Ideas 1-3 were the
first batch; 4-9 the second.

Fleet roles use window indices from [fleet.md](fleet.md):
`a0/a1` = opencode + Ox Alpha (cheap throughput / reasoning),
`a2/a3` = opencode + Muse Spark (creative),
`a4/a5` = command-code (fast code workers).

---

## 1. Crypto Shorts Factory (daily 9:16)

Daily automated short: signal -> script -> HyperFrames composition -> render -> publish.
Base: e035 (alerts), e025 (tails), e024 (diffusion studio), e030 (avatar), e027 (design).

| Agent | Role |
|---|---|
| a0 | Scout — poll Hyperliquid REST for S/R proximity + tail extremes -> `signals.json` |
| a1 | Quant — validate vs volume profile (e022), write `SCRIPT.md` |
| a2 | Director — build composition, apply DESIGN.md brand |
| a4 | Renderer — `hyperframes render` with VAAPI |
| a5 | Publisher — YouTube API upload, trail.md log |

Handoff via file inbox (`watch-agents.sh` pattern already in e000-fundamentals).
~2h end-to-end per video. Monetizable: views + Hyperliquid affiliate.

## 2. Undetectable Alpha Harvester

Extend e020 benchmark loop against gated sources (X, Polymarket, Kaito): measure
success/captcha rate per stealth browser; fall back to APIs when blocked; convert
harvested alpha into explainer videos (e032 style). Output: report (e011 style) + video.

## 3. Live Trading Desk with Avatar

24/7 desk (e036 `desk.py`) + replay buffer (e006); VRM avatar presenter (e030)
narrates signals via TTS; HT-coach risk filter (e008) acts as emotional
circuit-breaker before any order. Fully local, zero web dependence.

## 4. Strategy Tournament

Each agent designs a strategy from e025 candle-tail data; head-to-head backtests on
Nautilus (e022), identical virtual capital, weekly elimination bracket; winner deploys
to live desk (e036). Split: a0/a1 rival designers, a2 arbiter/code review, a4 backtest
runner, a5 renders "Tournament Ep. N" leaderboard video. Serialized content + you keep
the winning strategy.

## 5. Crypto Bounty Hunter (direct crypto income)

Algora/Polar/GitHub bounty APIs -> agents hunt issues, collaborative fix (one
reproduces, one patches, one reviews), claim in USDC. Only idea where agents
*generate* crypto rather than talk about it. a4/a5 as patch workers, a0 scout,
a2 QA gate.

## 6. Prediction Market Debate Podcast

Polymarket/Kalshi odds via API; two agents debate bull vs bear with real data;
VRM avatar presents (e030, e002); vertical podcast output. Track record is scored
against actual market resolution — measurable credibility.

## 7. Whale Radar

Hyperliquid websocket: giant position opens/closes/leverage changes -> ntfy alert +
auto-rendered mini-video explaining what the whale did and why it may matter.
Target <5 min event-to-publish. a0 listens, a1 contextualizes (funding/OI),
a2-a4 render, a5 publishes.

## 8. Agent Arena (public self-benchmark)

The five agents compete on real tasks drawn from p4 experiments (render a video,
fix a bug, analyze data). Public Elo table, published as "5 AIs walk into a
terminal" series on e023. Meta-marketing: the channel documents itself.

## 9. Build the Missing Browser Tool

Stop dodging the browser problem — productize it: CDP-direct wrapper with session
persistence, fingerprint rotation, captcha detection -> API fallback queue.
Publish as OSS + video "we built the browser tool AIs keep failing to use".
e020 is the ready-made benchmark to prove whether it works.

---

## Suggested order

1. #1 Shorts Factory — fastest launch, all-local, reuses 6 experiments.
2. #8 Agent Arena — free marketing for everything else.
3. #9 Browser Tool — long shot but builds a durable asset.
