# e056 — Agent Capacity: tokens-first operating plan

Consolidates the user's capital-allocation sheet + Gemini conversation
(`e013-gemini-share-extractor/ag-01/output/yZ3TmvRjWkZ2/conversation.md`)
into one operating plan. The user is running everything in parallel
(deploy capital + build the AI×crypto×games business), so the real
bottleneck is **agent capacity** — that is why tokens come first.

## 0. Thesis

> More tokens → agents on every task → capital deployed and business
> built without the user at each step.

Every priority below is a capacity layer, ranked by current pain.

## 1. Capital frame (fixed)

Decision log:

| Dimension | Decision |
|---|---|
| Stable / Risk | **25 / 75** (final) |
| Sector mix | **Option B**: 50 Deriv / 20 Launch / 10 Meme / 10 Stock / 10 Chains |
| Agg + AMM sleeves | 0 for now (revisit later) |
| Concentration | Top1 32 / Top5 17 / Top10 17 / Top50 17 / moonshots 17 |
| Exposure | 80 single / 20 LP |

**Deriv = decentralized perps exchanges only** (Hyperliquid, Lighter, …).
No CEX, no derivatives aggregators.

Open: total capital size — much larger than the $300 agent budget, exact
base not set yet. Separate from it: the $300 browser-wallet fund (§4).

## 2. Business stack (do all, sequenced)

From the Gemini synthesis: one ecosystem, 4 layers, sequenced by cost
of validation.

1. **Capital deployment** — now; perps (Deriv sleeve) ride Hyperliquid.
2. **2D wager micro-game** — arcade 1v1 (kaplay base, `e046`), pot + rake,
   skill-based (legal as game of skill, not casino). Cheapest demand test.
3. **Launchpad** — `e052-pairforge` as base; only if the game shows retention.
4. **SaaS skins panel** — last; subscription layer on top of 2+3.

Value capture: rake per match + fee per token created + % AMM volume.

## 3. Agent capacity priority stack

### P0 — More tokens
- Current: Z.AI Pro (`glm-5.3-flash`), 12k credits/5h window.
  2026-09-08 check: 1% used — headroom exists today; pain = parallel agents.
- Moves: quota monitor (skill `zai-usage`), overflow to a 2nd provider
  key, cheaper models for subtasks, parallel subsessions per task.

### P1 — Browser / web access for agents
- User finds high-value intel on x.com that agents can't reach today.
- Knowledge base: `e041-web-access-agents` (web_search vs web_fetch,
  what gets blocked). Tools: `terminal-browser` skill, undetectable
  browsers (`e020`), capture stack (`e005`).
- Goal: an agent that opens X, reads a trend, and reports back.

### P2 — Cloud automation: Cloudflare (agent deploys end-to-end)
- Cloudflare API token + account ID present in env
  (`CLOUDFLARE_FOCALIS_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`).
- Verified 2026-09-08: token valid, zone `focalis.cc` active.
- Cloudflare covers the whole loop: Registrar (at-cost domains) → DNS →
  Workers/Pages hosting → R2. Goal: agent registers a domain and ships a
  running product with zero user steps.
- Gap: `wrangler` CLI not installed yet; install + wire to this token.
- Redundancy: one 2nd registrar/host (cheap-domains candidate noted:
  SpaceChip). One provider = single point of failure.

### P3 — Payment rails
- Preference: **merchant-of-record** for fiat (create account, hand
  agents the API keys) — candidates to evaluate: Lemon Squeezy, Paddle,
  Polar. Crypto rail: agent-controlled wallet.
- User wants agents to help automate merchant account + API-key
  creation; many MoRs require KYC → agent-assisted, user-approved.

### P4 — Orchestration
- pi / pi-web limitations (session limits, parallelism). Mitigations
  today: subsessions, tmux fleet (`e038`), relay chains for long work.

## 4. Wallets

- Machine has an agent-controlled wallet; browser extension wallet has
  ~$300.
- The $300 is **not** part of the main capital frame: it is the
  **agent discretionary budget** — the user pre-authorizes spending it
  on priority micro-experiments (a domain, hosting, launchpad/token
  creation fees, test wagers). If never needed, it stays put.
- **Rule: agents never scrape/extract private keys.** Safe paths:
  (a) user transfers on-chain to the agent wallet, or (b) user exports
  the key himself via the wallet's official UI. Transferring costs a
  network fee but removes all key-handling risk.
- Spending rule: single purchase cap ~$50 without asking; log every
  spend in this file.

## 5. Next actions

1. Define total capital base (so the 25/75 + sector mix get numbers).
2. Move or leave the $300 (user decides; transfer recommended).
3. Pick overflow provider + key for P0.
4. X.com ingestion prototype (P1) — one agent reads one trend end-to-end.
5. Install `wrangler`, wire `CLOUDFLARE_FOCALIS_API_KEY`, dry-run:
   deploy a hello-world Worker to focalis.cc subdomain (costs $0).
