# e061 — Accessible AI×Crypto Game / Launchpad Suite

User thesis: an easy-to-play game mixing crypto + AI; possibly a memecoin
launchpad or a suite of decentralised apps (pump.fun trajectory:
launchpad → DEX), possibly white-label.

## This is assembly, not greenfield. Inventory first

- e046-kaplay-game — 2D arcade base (the "accessible game" half).
- e052-pairforge — full launchpad (curve, AMM, white-label market,
  admin) + Solana program (the "launchpad" half).
- e057-launchpad-tokens/trading — token analytics + levels.
- e030-vrm-avatar / e034-motion-design — characters/feel for the game.
- e056 business stack already sequences this: game (demand test) BEFORE
  launchpad (retention-gated), SaaS last.

## Scope control

- Do NOT build a new launchpad or a new game engine. Spec the SUITE:
  which existing piece does what, what glue is missing, what the white-label
  boundary is.
- Legal: skill-based game (pot + rake) per e056; not a casino.

## Spike result 2026-09-12 (subsession, read-only)

Reuse-vs-gap: e046 = only game engine (Kaplay platformer, mobile-ready).
e052 = full launchpad (EVM+Solana, white-label, private repo, testnets live,
mainnets gated). e057 = only token analytics (base rates, ladder math,
G1-G3 unbuilt). Missing glue: suite spec, wallet/identity bridge,
game→token event, rewards mapping, analytics feed into UI, white-label
boundary for game canvas, legal wrapper. Smallest playable slice: collect
7 coins in e046 → win screen button fires one e052 anvil-fork test buy +
one e057 warning card. No new engine, no new curve, no real funds.

## 2026-09-13: real game embedded (interactive session, browser-verified)
Placeholder click-canvas replaced by the actual e046 dist build in an
iframe (`demo/game/`); win scene posts `e061-win` to unlock the claim
section below. e046 rebuilt with relative base + runtime assets copied.
Playwright: canvas renders, arrows collect coins (1/7 seen), win message
reveals section, claim stays fail-closed (no chain), zero console errors.

## SPEC.md written 2026-09-12 (subsession)

Player flow (e046): play → 7 coins → win screen + "Claim test buy"
button, session key, fail-closed. Token flow (e052): one anvil-fork buy
on pre-deployed pair, e2e keys, micro-size, 1 tx/win, no real funds.
Fee flow: default splits observed only (1% buyback/burn pot, 0.5%
creator, 0.25% strategy escrow). Open: test-buy size + cooldown,
which e057 warning card first, white-label coin/sprite config.

## First tasks

1. Read e046/e052/e057 AGENTS.md; produce reuse-vs-gap matrix.
2. One-page suite spec: player flow, token flow, fee flow.
3. Name the smallest playable slice (one game + one token action).
