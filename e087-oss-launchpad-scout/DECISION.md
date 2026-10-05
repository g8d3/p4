# DECISION.md — locked 2026-10-05 from user answers

User verified with adjustments (answers in Spanish, locked here in English):

1. Trends: user did not fully parse A1–A5 ("no entendí mucho").
   Lock = A1 core only (OSS-backed token launchpad on Solana), others are
   supporting rails, not the headline. Plain statement: anyone creates a
   token backed by 1+ OSS projects; buyers support contributors and share
   profits. Confirmed gap: TEA is on Base, nothing verified on Solana.
2. Backing = REVENUE-SHARE ONLY on real monetization. Money flows to OSS
   repos ONLY when the repo is providing real value inside a monetized
   AI-generated app with paying users. No earnings = nothing to split.
   Example locked: user asks agent to build an app from 4 OSS repos; agent
   builds it; payouts happen only from actual user payments for that app.
3. Funding-arb = BOTH (scanner feature + treasury story), user unsure if
   both is wise. Resolution: ship scanner widget first (visible value),
   treasury use second and labeled experimental.
4. Game = FULL game in prototype, built by reusing an existing OSS game
   (saves dev, dogfoods the OSS-reuse thesis). No from-scratch game.
5. Payments = fiat merchant-of-record + direct crypto. NO x402 assumption.
   Open research: crypto refunds/guarantees ( pleasing like card
   chargebacks) — survey escrow / payment-processor refund support and
   integrate what exists.

## Prototype scope (Phase 3, ponytail discipline)

- `server/app.py` stdlib only, reads `needs.json` for port/paths.
- `public/index.html` single file, tabs: Launch | Projects | Game | Funding | Pay.
- Launch: create token bound to 1+ OSS repo URLs (stored locally, no chain tx).
- Projects: each OSS repo shows earnings accrued + payouts due (zero until
  a payment event references it — enforces rule 2).
- Game: one embedded OSS game whose sessions can generate payment events.
- Funding: read-only scanner placeholder (static sample + venue note).
- Pay: two buttons — fiat MoR (stub checkout record) and crypto (stub
  payment record with tx placeholder); every payment optionally references
  repos to split; refunds table documents guarantee handling.
- Gate: `bin/check.sh` — health + tabs + rules (zero-payout-when-zero-revenue).
