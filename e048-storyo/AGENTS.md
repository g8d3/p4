# e048 — Storyo.cc — CLONED & REBRANDED ✓

**Storyo.cc — rebrand of infiniteslop.ai clone live at `http://127.0.0.1:8180/` · faithful mirror at `/original`** — Habbo-style chat, 9:16 vertical TV, HLS live playlist, swipe reel, hearts, queue/votes, holographic "my prompt" glow — identical 68KB HTML + 406KB hls.min.js. Proxy keeps LIVE data fresh from origin.

Original concept: infinite interactive AI live stream with persistent memory, branching timelines, and progressive quality ladder.

Inspired by levelsio/infinite-slop (Minimax H3 Max @ fal, $0.025/s at 480p -> $0.05/s soon). This is the leveled-up version: memory + branches + monetization as open garden.

## Concept

- **Single infinite channel** at start (web + RTMP to YT/TikTok). Architecture ready for multichain channels.
- **Branches:** every clip ends with 3 LLM-suggested branches + dictation (Web Speech API) + custom prompt (paid). Votes are free, custom prompts are paid. Branches with support level up in quality.
- **Progressive quality ladder (cost control):**
  - L1 Trial (cheap test): generate with Minimax Max 480p but playback at 4-6fps (we drop frames) OR Flux+Fish TTS slideshow if fps trick fails. Cost ~$0.025/s.
  - L2 Supported: Max 480p @ 24fps native
  - L3 Premium: Max 720p/1080p @ 24fps native
  Only supported branches level up. Keeps 4h/day at ~$60-120 instead of $360.
- **Memory (slop -> story):**
  - Visual: Character Bible JSON + CLIP embedding of last frame passed as image_condition
  - Narrative: Living summary (300 tokens, LLM-maintained) + vector DB for lore
  - Chaos: 85% coherence / 15% surprise injection via LLM rewriter
- **Agents:** fleet of writer agents fills gaps when chat is silent, suggests branches

## Payments (sustainable open garden)

Abstract `PaymentProvider` interface - two rails, same queue:

- **Fiat / Merchant of Record:** Dodo Payments (primary MoR, handles tax/VAT globally) or Whop (alternative). `POST /api/pay/mor` -> webhook -> enqueue prompt. Covers cards, Apple Pay, etc.
- **Crypto Multichain:** Helio / DePay / NOWPayments style provider (EVM + Solana + Base + HYPE). `POST /api/pay/crypto` -> verify on-chain -> enqueue. USDC on Base as default.
- **Consumer -> Producer flywheel:** free vote -> $1 custom prompt -> $5 branch fork -> $19/mo own channel (70% rev share)

## Admin Feedback Interface

`/admin` (password protected) is the dev feedback loop - no need to use external chat:
- Live cost dashboard (spent / earned today)
- Queue + rewritten prompt preview
- Character Bible + Living Summary editor
- Per-clip feedback: 👍 coherent / 👎 broke / 💡 idea -> writes to `data/feedback.jsonl` for agent tuning

## Stack

- Next.js 15 + Tailwind (mobile-first) + fal-ai JS SDK (Minimax Max)
- FastAPI or Next API routes for queue/worker, SQLite (WAL) for jobs like e044
- Web Speech API for dictation, ffmpeg for fps downsample
- `app/payments/` abstraction: `mor.ts` (Dodo/Whop adapter) + `crypto.ts` (Helio multichain adapter)

## Clone (live)

```bash
./bin/run.sh          # clone at http://127.0.0.1:8180/ (proxy → https://infiniteslop.ai)
```

- `clone/original.html` — identical mirror of infiniteslop.ai (68KB)
- `clone/index.html` — rebranded Storyo.cc (same engine, new logo/title/og)
- `clone/hls.min.js` — 406KB
- `clone/live/poster.jpg`, `clone/og.jpg` — assets
- `server.js` — static + proxy (`/api/*`, `/status.json`, `/live/*` → origin, CORS open)
- `sites/storyo.cc/` — static copy for deploy

Verify faithful: `curl -s http://127.0.0.1:8180/original | diff - <(curl -s https://infiniteslop.ai/)` → identical.
Verify branded: `curl -s http://127.0.0.1:8180/ | grep Storyo` → branded.

## Run (original multiverse concept)

```bash
./bin/run.sh          # same entry, serves clone
./bin/test-fps.sh     # benchmark $5: Test A/B/C fps trick (TODO)
```

## Costs (Minimax H3 Max)

- $0.025/s @480p (now) -> $0.15 per 6s clip -> $90/hour -> $360 per 4h day
- $0.05/s @480p (soon) -> $0.30 per 6s clip -> $180/hour -> $720 per 4h day
- Need ~6x $1 prompts/minute to break even at $0.025/s. Ladder keeps trial branches cheap.

## Inherits

- [../AGENTS.md](../AGENTS.md)
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md)
