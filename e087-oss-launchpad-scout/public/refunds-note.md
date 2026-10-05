1. Solana Pay: open split/escrow via reference keys; refunds are manual new transfers, no chargebacks — stub logs a refund record.
2. Helio: hosted Solana checkout with dashboard refunds for card/crypto orders — stub covers the record, not the dashboard action.
3. Stripe crypto: card-style dispute flow on on-ramps, on-chain sends final — stub marks refunded + zeroes splits.
4. Jupiter/DEX swaps: irreversible once filled; guarantees need an escrow vault holding funds until delivery.
5. Squads/Multisig vault: 2-of-3 escrow, refund = proposal executed back to buyer — stub mimics the state flip.
6. Cardinal/escrow programs: time-locked release, expiry auto-refunds — stub skips the program, keeps expiry note.
7. MoR (fiat): provider handles chargebacks/guarantees natively — stub stores a checkout record only.
8. Disputes: crypto has no processor reversal; policy is re-transfer + signed memo, documented per payment.
9. Prototype rule: POST /api/refund zeroes that payment's splits and tallies them under refunded, never deleting history.
10. Path forward: pick Helio (hosted refunds) or vault escrow (Squads) before mainnet; current stub covers records only.
