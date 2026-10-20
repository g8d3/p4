# FiloEterno direction: build + audit real-value dapps (decided 2026-10-18)

## The decision you asked me to help with

Memecoins earn from volume. Volume needs attention. Attention needs novelty.
But novelty dies fast — unless the coin does something useful. So:

**Build memecoins that pay for themselves twice: volume fees AND service fees.**

Each launch = a meme token + one tiny real service glued to it. The meme brings
eyes (cheapest marketing in crypto). The service brings revenue that does not
depend on hype. Examples of the pattern (first build picks one):

1. **Tip-jar coin**: token with a 1% transfer fee streaming to a treasury that
   funds holder-voted micro-grants. Value: on-chain patronage, visible pot.
2. **Gated-tool coin**: holding X tokens unlocks a real tool (fee tracker,
   alert bot, portfolio page). Value: the tool; the token is the key.
3. **Lottery coin**: fees feed a weekly on-chain lottery for holders.
   Value: entertainment with provable odds (not a promise, code).

Why this direction wins for a self-improving loop:
- One codebase pattern (token + treasury + service) reused forever — the loop
  compounds instead of starting over.
- Scoreboards are automatic: tests pass, audit findings, fees collected on
  testnet, deployment receipts.
- Contracts + fullstack + trending research in every round: read the trend,
  launch the variant, audit it, keep the lesson.

## What is NOT the direction

- Pure meme with no service (dies with the trend, nothing learned).
- Trading the coins (paper signals stay a side task; money never in the loop).
- Mainnet with real funds until a human approves an audit gate (locked rule).

## First project (queued)

`tasks/01-tipjar-coin`: ERC-20 + 1% fee treasury + holder vote contract,
Hardhat/Foundry tests, self-audit round, local-only deploy receipt.
Score: tests green + audit checklist + gas report.
