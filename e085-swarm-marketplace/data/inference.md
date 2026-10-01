# Inference comparison (inference-scout, 2026-10-01)

Owner note: "command code" = **Claude Code / Anthropic API** (pending owner confirm).
Default stays **OpenCode Zen** (`OPENCODE_API_KEY`, base URL from `needs.json`
`inference.base_url_env`). No keys below — env names only.

Prices = USD per 1M tokens, **input / output**, standard tier, checked 2026-10-01
via provider pages + search. Providers reprice often — re-check at billing time.

| Provider | $/1M in/out (anchor models) | Strengths | Batch / cache |
|---|---|---|---|
| **OpenCode Zen** (default) | Pass-through, **zero markup**: e.g. Sonnet 5 ~$2/$10, Opus 5.5 ~$4/$20, Muse Spark $1.25/$4.25 | Curated + benchmarked for coding agents; any-agent OpenAI-compatible (`.../zen/go/v1/`); $20 prepay + spend caps; US-hosted, zero-retention | Inherits underlying provider's batch/cache |
| **Anthropic API** (Claude Code) | Sonnet 5 $2/$10; Opus 5.5 $4/$20; Opus 5 $5/$25; Haiku 4.5 $1/$5 | Frontier coding quality; native tool use, prompt caching, batch | 50% off batch; cache read ~10% ($0.20–0.30/M) |
| **OpenRouter** | Underlying + **5.5%** fee: Sonnet via OR ≈ $2.11/$10.55 | 500+ models, one key, auto-fallback routing | Pass-through where provider offers it |
| **Together** | gpt-oss-120B $0.15/$0.60; Llama 3.3 70B ~$1.04/$1.04; GLM-5.3-Flash $0.15/$0.50 | Cheap open-weights at scale; fine-tune; dedicated endpoints | Cache ~10–20% on listed models; batch API |
| **Fireworks** | gpt-oss-120B $0.15/$0.60 (same class as Together) | Fast serverless; fine-tunes served **at base price** | Standard/priority/fast tiers; cache on listed models |
| **Groq** (LPU) | Cheapest bulk: Llama 8B-class ~$0.05/$0.08; 70B-class ~$0.6/$0.8 | Lowest latency; generous free tier → sandbox runs | No batch; speed IS the feature |
| **Gemini** | Flash 3.7/3.8 **$0.75/$3.75** (→ $1.50/$7.50 Jan-2027); 1M ctx; free tier | Cheapest frontier-class; grounding (Search/Maps); no-training-data paid tier | **50% off batch** ($0.375/$1.875); cache $0.075/M + storage |

## Verdict for swarm marketplace metering

- **per_token**: meter at provider rate + `fee_bps` (500 = 5%). Keep **Zen default**
  (quality + zero markup + spend limits). Cheap lane: **Gemini Flash** (frontier
  ~$4.50/1M in+out, batch ~$2.25) or **Together/Fireworks gpt-oss** (~$0.75/1M).
- **per_result**: price is set by the SELLER ($/accepted result), not by inference.
  Inference cost is the seller's margin problem. Needs the result oracle
  (accept/reject window + auto-accept + idempotent ledger) before real money.
- **per_run**: flat price must cover p99 token cost → route bulk runs to
  Groq/Gemini-Flash, keep frontier runs on Zen/Anthropic.
- Recommendation: **Zen = default, Gemini Flash = budget default, Groq/Together-oss
  = bulk lane, OpenRouter = fallback aggregator only** (fee + no quality edge).
  Real metering needs provider usage API wired to `/api/orders` (see `data/needs.json` → `meter`).
