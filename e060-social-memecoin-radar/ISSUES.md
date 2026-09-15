# e060 ISSUES — agent review 2026-09-13 (prompted by owner: "the agent should have ideas")

Essence lives in `p4/e000-fundamentals/UX.md`. Agent ideas go public in
`p4/IDEAS.md` first (board renders them), instances land here.

## 1. Decode the pulse line (UX §8)

Today: `LIVE 15 tokens · sample 2m ago (every 5m) | worthy score… |
v<hash> [STALE—restart]` — same disease e058 had: bare `v` hash,
`|`/`·` separators, dev-speak (`STALE—restart`). Wanted: labeled
subsections (`data:`, `paper:`, `version`), words a stranger gets.

## 2. Paper ballot section (UX §3, same pattern as e058 #8) — SHIPPED run #72

18 pending calls, no visible list (early expand shows a few).
Wanted: titled ballot — coin, entry, called-how-long-ago, status.
Shipped: <details id=ballot> + /api/paper pending_calls (one line per
pending snapshot: coins, called Xh ago, grades in Yh).

## 3. Call time windows (UX §1) — SHIPPED run #72

Entry→now prices exist; the *when* doesn't travel with them.
Wanted: every call carries `called Xh ago` + first-grade countdown.
Shipped: ballot rows carry called-ago + grades-in per snapshot (server
+ JS refresh from /api/paper pending_calls).

## 4. Kill-clock on the card

Kill rule (no signal in 2 weeks → kill track) is invisible.
Wanted: track age vs rule on the card — day X of 14.

## 5. Bank rotation snapshots as price history (THIN cure)

Free tier has no history — but 5-min rotation samples ARE history.
Wanted: persist them; in ~2 weeks the track owns a backtest series.

## 6. Heat breakdown on tap (UX §7)

Formula buried in a details block. Wanted: per-row `why this heat`.

## 7. Param review trigger at N≥20

heat≥80/vol/txns never re-fit. Wanted: dated refit trigger, not intent.

## 8. Lineage on-card (UX §15, doc shipped 2026-09-13)

`LINEAGE.md` holds the full source→table→filter flow with formulas.
Wanted next: the card itself links each number to its recipe (tap
`heat` → formula + inputs), and a pipeline strip naming the 7 stages.

## 9. Real social input (queued 2026-09-13)

The radar measures bought attention + velocity; zero social input.
Order: free first (Alternative.me Fear&Greed, no auth — market-wide
mood column), then quote paid per clone-before-pay (LunarCrush,
Santiment) + social-API directory (sibling to the web3 one).

## Standing observation

Legs keep shipping verdict guards while score sits 0/0
(blocked-on-time). Copy polish during measurement-wait is motion
without movement — rank measurement and UX-law violations above
wording guards until first grade lands (~2026-09-14).

## 5. Thin flag on shadow bars (UX §7 honesty, found run #130 as owner)

Opened the card as the owner: `stricter bar 60.0% (3/5, trying)` reads as a
winning system, but N=5 is THIN (rule: N<20) and the API already said
thin:true — the card just didn't render it. Same for looser bar (3/9).
Fixed run #130: card appends `· thin` from `p.shadow.thin` /
`p.shadow2.thin` next to each bar; e2e PASS, running==latest after restart.
Story: never let a small percent travel without its sample size on a phone.
