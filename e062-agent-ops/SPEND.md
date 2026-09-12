# SPEND — business autonomy policy (agents decide + spend inside these lines)

Why funded wallets exist: agents must be able to act (fees, domains,
micro-tests, API trials) without waking the owner per $0.30.

## The fund (corrected 2026-09-12: single $300 fund)

Total: **$300**. Deployed to agent wallet `0x6646...` on Arbitrum One:
**100.47 USDC + 0.00435 ETH** (~$111: $100 bankroll + ~$11 gas).
~$189 remains with owner. Runway `left` counts against the full $300;
the deployed $100 is inventory-in-place, not spent.

## Tiers

- **T0 — free ops**: read APIs, local compute, polls. Unlimited, just log.
- **T1 — auto-spend ≤ $50 per action, per track**: gas, bridge fees,
  domains, test positions, cheap API trials. Execute + log every spend
  (track, amount, tx/id, reason) in the experiment file. Pre-authorized
  by owner (matches e056 $300 discretionary budget).
- **T2 — above $50 or irreversible**: write a **proposal** to the ops bus
  (`ops.py propose`), notify owner (ntfy), wait. Owner approves in chat
  (`ops.py approve <id>` or plain "yes <id>"); the NEXT agent run
  executes and marks `executed`. No self-approval, ever.

## Hard lines (no exceptions)

- **No KYC bypass**: no fake identities, no ID forgery, no circumventing
  sanctions/geo-blocks, no straw accounts. KYC-gated services wait for
  the human — propose, don't impersonate.
- **No ToS-breaking account farming**: automated creation only where
  self-serve + allowed (see green list). Rate limits respected.
- **One wallet per blast radius**: agent funds never mix with owner savings.

## Service lists (living)

- GREEN (self-serve, no/low KYC): EVM/Solana keypairs, Hyperledger-style
  DEX accounts (key = account), Cloudflare (token present), free-tier APIs,
  ntfy, GitHub repos,5555 testnets/faucets.
- YELLOW (email/phone-gated): free trials needing verification — propose
  first, owner supplies the human step once, agent continues.
- RED (KYC/money-transmitter/CEX withdrawals to fiat): human only.

## The wheel (owner order 2026-09-12)

No endless money: every spend must have a return path or be a bounded
probe with a kill rule.
- **Tiers of money**: opex (gas/fees, sunk) vs capex (domains/keys that
  persist) vs inventory (positions that earn). Log kind in the note.
- **Probe → scale**: first probe tiny (a few $); scale only survivors
  (persistence + net-positive measured, not hoped).
- **Recycle**: earnings refill the pool (`ops.py earn`) — funding income,
  API revenue, referrals. The pool grows by returns, not top-ups.
- **Runway**: `ops.py runway` — spent/earned/left per track, on the board.
  Track with no returns after 3 funded probes gets proposed for kill.
- Agents default to spending-to-finish; this section overrides that:
  **finish mysteriously cheap, or don't finish yet.**
