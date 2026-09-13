# e061 ISSUES — owner review 2026-09-13 (game looks frozen for hours)

Essence lives in `p4/e000-fundamentals/UX.md`.

## 1. The stall is the metric, not a bug (root cause)

Score = day-2 returns, but day-2 lives in per-device localStorage
(`e061-visits`, `e061-runs`) with NO server log. No human returns →
score can't move → legs polish cosmetics (header, iframe size) while
blocked. The owner sees the same screen for hours and reads it as
broken. Wanted: server-side play log (every play/run/slip POSTed,
countable per day) + metric redesign: verifiable day-1 proof
(completions, slips created/shared) alongside the day-2 gate, so the
track moves daily with or without returning traffic. Queued for legs.

## 2. Dead claim path decoded (UX §7, fixed 2026-09-13 direct)

`Disabled (fail-closed): pair not deployed / chain not anvil
(expected: slice is fail-closed without e052 anvil-fork)` →
`Test buys locked: test buys unlock when the demo coin is deployed
(not yet — play and paper slips work now)` (status.json +
index.html fallbacks). Behavior unchanged (still locked, honestly).

## 3. Slip jargon decoded (UX §7, fixed 2026-09-13 direct)

Slip shared `kill rule: no CONFETTI buys…` + `fee note: … observed
only` → `safety: only touch tokens that have a level and a quit
line` + `fees: 1% pot / 0.5% creator / 0.25% escrow (watched, not
charged)`. What the player shares must read clean (UX §6 preview).

## 4. Remaining dev-speak (UX §7, for legs)

Spec-slice paragraph (`fail-closed`), fees section (`observed
only`), stats `unattested` — decode or move behind tech half.
