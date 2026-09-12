# e061 — Game / Launchpad Suite Spec (smallest playable slice)

Assembly only: e046 = game canvas, e052 = launchpad (private repo, anvil-fork e2e only), e057 = analytics math, e056 = skill-game legal frame. No new engine, no new curve, no funds, no mainnet.

## Player flow (e046)
Start scene → platformer (run/jump, touch + keyboard) → collect 7 coins → reach green goal → win screen. Win screen gains one button: "Claim test buy". No wallet login in slice; browser session key only.

## Token flow (e052, test only)
Win button → single buy on one pre-deployed anvil-fork pair (existing DeployAll manifest) → e2e keys only, fixed micro-size, one tx per win. Fail-closed: pair not deployed or chain not anvil = button disabled with reason. No mainnet/testnet funds move.

## Fee flow (rake + fees accrue in e052)
Match pot (if wagered, future) → rake to PairManager pot; test buy → 1% platform (buyback/burn pot) + 0.5% creator + 0.25% strategy escrow (capped 80%). Slice only observes the 1% on the test buy; no distribution, no withdrawal.

## Analytics card (one e057 warning)
Under win screen: one card — base-rate warning (most launchpad tokens → 0; entry needs level + kill rule per STRATEGY.md). Read-only text + fairLaunchScore/staleness if attested, else "unattested". No charts, no G1-G3.

## White-label boundary
Rebrandable: e052 PFConfig `brand.*` keys + game title/sprite/coin count via config. Not rebrandable in slice: engine (Kaplay), curve math, fee splits, EIP-712 attestation format.

## Legal note (e056)
Skill-based game (pot + rake, arcade 1v1 demand test), not a casino; launchpad gated on game retention; SaaS last. No real-money wagering in slice.

## Glue missing (after slice)
Wallet/identity bridge, game→token event bus, rewards/XP mapping, analytics feed into UI, game-canvas white-label keys, legal wrapper text.
