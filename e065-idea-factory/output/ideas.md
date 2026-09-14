# Idea bank — first table (seed, pre-sync)

Seeded 2026-09-14 run #82 from fleet context (e064 sync still pending —
vault has no X session yet). Every row below is brainstormed BEYOND any
liked post: no feed exists yet, so all novelty is agent-side. The next
leg re-ranks this table against the first real sync.

| idea | evidence | novelty | effort | score |
|---|---|---|---|---|
| Arc-chain dApp directory with per-app numbers (TVL, txns, users, fees) from day one | Arc launch chatter across the fleet brief (~1–2 days to launch) + owner ordered e066 | transplant: DefiLlama-style atlas for a chain at birth | M (new app, e066 owns) | 9 |
| Funding-rate steady-pay scanner as a phone card (e058 data put to work) | e058 holds 51.7% over N=466; owner already gets conclusions-only pings | package: paper-tracked pays, no new data | S (card section) | 8 |
| Cheap-vs-peers weekly ping from static multiples (e059 paper loop, 30d resolves) | e059 precision 0.952 backtest, 20 paper pending | repurpose: read-only alert, no trading | S (copy + threshold) | 7 |
| Rotation radar worthy-call countdown as a shareable pretty page | e060 per-call ballot countdowns live, first grade due ~05:30Z | shareable page, not clipboard (UX law) | S (page template) | 7 |
| Game launchpad day-2 loop: win → paper slip → claim reminder ping | e061 visits 11, players 2, day2=0 — traffic, not product, is the block | invert: reminder brings the player back, not a new feature | S (ntfy on win+24h) | 6 |
| Tax-report-ready money log export (every spend/earn with tx hash → CSV) | owner TAX standing order 2026-09-14; e062 ledger already keeps tx_hash | compliance as product: one-tap export | S (ledger query) | 8 |

| e062 one-tap approve card on the phone (proposal #5 pattern → every gate) | e064 login handoff + money gates both wait on owner taps; e063 money-gate cards exist but rung-4 needs the tap | compress: every owner decision becomes one exact-asking card with sane default | S (card template) | 7 |
| e060 early-loss guard: auto-flag calls down >50% before 24h (BLAST -73% seen) | run #83 paper read: 2 early calls avg -86.4%, 0 resolved — losers show before grades land | repurpose: read-only risk badge, no trading | S (threshold + badge) | 7 |


| Thumb-bar approve everywhere: e062 gate1 pattern copied to e063 + every money card | run #84 shipped gate1 (first pending gate w/ approve+reject in bottom thumbbar, e2e-locked) — same one-tap ask works for all gates fleet-wide | transplant: one proven control, zero new auth | S (copy render block) | 8 |
| e061 day-2 nudge from fresh traffic (visits 13->15, players 2->3 overnight) | run #84 stats: new player arrived with zero product change — a win+24h claim-reminder ping converts ambient traffic into day-2 redeems | repurpose: ntfy already wired, no game change | S (win timestamp + ping) | 7 |
| No-JS version+change line on every static page (e061 baked v+sha fallback) | run #85 phone check: e061 version badge renders empty until fetch resolves — blank on slow phones, owner can't see what moved | transplant: bake `v<sha>: one plain sentence` in HTML, JS overwrites when live | S (one line + keep fetcher) | 7 |
| Paper grade countdown on the card (e058 grades ~05:04Z, e060 ~05:33Z) | run #85: both trading tracks blocked-on-time with known due times, but the card shows no countdown — owner can't see when proof lands | package: read-only countdown from logged_ts+24h, no trading | S (card line + max ts) | 7 |
| Paper grade due-date line on every trading card (e059 ships 10-14) | run #86: e059 score line gains `first grades 10-14` from pending dates + resolve_days — same one-line due-date works for e058/e060 tightening their Xh countdowns | transplant: one proven line, zero new data | S (due-date fn) | 7 |
| Server-side day-2 due counter (e061 ships wins24+due) | run #86: e061 /api/stats names wins in 24h + cids due back now — same due-now counter pattern fits e058 paper grades the hour they land | repurpose: read-only counter, no ping | S (stats field + line) | 7 |

Rising themes: proof-countdowns (new) · one-tap approvals · Arc-launch · read-only alerts over trading.
| CATFLIGHT autopsy: compare entry-age of e060's first hit vs 4 misses (run #87: 1/5, only +2.6% held) | run #87 grades: 4 misses bled -17% to -99% in 24h, all ex-pump names — entry delay may predict the bleed | repurpose: read-only autopsy, no trading | S (entry-ts vs outcome) | 7 |
| e058 streak board: coins holding 3+ straight days get a streak mark on the card | run #87 backtest 54.1% (279/516) — persistence is the edge, streaks package it for the phone | package: read-only badge, no new data | S (consecutive-hold count) | 6 |
| Shadow-bar pattern to e058 steady calls: paper-track a stricter tier (e.g. min-legs 3 + spread floor) beside the live backtest, promote only at N>=20 (run #88: e060 shadow 1/2=50% vs live 1/5=20%) | transplant: one proven pattern, zero new data | S (shadow fn + line) | 7 |
| Tax CSV auto-attached to money gates: every approve/reject card links the current ledger export (run #88: /api/tax/export live, 3 rows) so the owner taps with the books beside the ask | package: read-only link, no new data | S (export URL) | 6 |
