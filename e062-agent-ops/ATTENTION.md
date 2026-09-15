# ATTENTION — do the agents think like the owner?

Every issue the owner finds first is a miss. Log it: what, where,
who found it, hours it sat unnoticed, why the legs walked past it.
Goal: owner-found rows get rarer and faster; agent-found rows (legs
fixing confusion before it is reported) are the real score.

| date | app | issue | found_by | hrs_unnoticed | why missed |
|------|-----|-------|----------|---------------|------------|
| 2026-09-15 | e058 | fixed thumbbar covers COINS table last rows at phone width (body pad 76px, inner-scroll table) | wander run154 | ~6 | pad set for page bottom, not inner-scroll tables; fixed: pad 76->124px + clearance-assert idea banked e065 |
| 2026-09-15 | wander | capture shelf bare at review (shots/ empty, no newest-shot age to check) | wander run129 | ~12 | capture cron writes nothing on quiet days and no leg asserted shelf age; fixed: review asserts newest-shot age first, beats wander-empty |
| 2026-09-15 | wander | shelf STILL bare at run130 review (2nd wander) — finding dies here per rule, converted to cron-health datum not a UX miss | wander run130 | — | no third log: capture cron (11:15+16:15 local) simply had not run; legs now read shelf age as cron health, not confusion |
| 2026-09-13 | e058 | signals show no time window (from→to present, why qualified) | owner | ~8 | legs polished copy, never asked "does the owner know what this signal IS" |
| 2026-09-13 | e058 | `urgent if bigger ×` label unreadable | owner | ~8 | config box shipped without read-aloud test |
| 2026-09-13 | e058 | filter covers main table only, silently skips signals | owner | ~8 | filter tested on one section, honesty rule didn't exist |
| 2026-09-13 | e058 | main section untitled (top/filters/alerts/signals named, main not) | owner | ~8 | no section-names rule |
| 2026-09-13 | all | config boxes stacked vertically, unaligned | owner | ~8 | no forms rule; AI-default stacking accepted |
| 2026-09-13 | all | paper slip = clipboard trick, never used; sharing needs a pretty page | owner | — | slip built for dev convenience, not human sharing |
| 2026-09-13 | e058 | top section undecodable: bare `flippy/legs swapping`, `(new)`, unlabeled `\|/·` stats, bare `v` hash, `paper 75 logged` with no when | owner | ~8 | dense line never read aloud by a leg; fixed direct 2026-09-13 |
| 2026-09-13 | e058 | paper ballot invisible: 75 predictions only in SQLite, /api/paper serves counts, no list anywhere | owner | ~8 | legs logged predictions but never asked "can the owner see the ballot"; queued as ISSUES #8 |
| 2026-09-13 | e058 | 4 signal pings in 2h: dedup keyed on sliding window, persistent payers re-pinged as URGENT | owner (screenshot) | ~2 | alert tested for sending, never for silence; 24h rule worked but 3 different coins pinged in 1h → escalated to digest-only (no owner action exists for any ping) |
| 2026-09-13 | e062 | board STALE—restart survives restarts | owner (screenshot) | ~1 | version scoped to whole dir incl. docs — my own doc commits re-dirtied after every restart; fixed: code-only scope (app.py/webauthn.py/static) |
| 2026-09-13 | e061 | game frozen for hours, same win screen | owner (screenshots) | hours | day-2 metric unmeasurable (localStorage, no server log) so legs polished while blocked; decoded dead-ends direct, server log + metric redesign queued |
| 2026-09-13 | e060 | trades link promises trades tab, tables fixed/read-only | owner | — | free API has no trades-tab URL (pair page only) → honest `pair ↗` label; SQL-grade grid + self-explaining scores queued (UX §9) |

## Rules for legs

- Open each app as the owner from the phone; ask the confused
  questions before the owner does. Fixes land in the app's ISSUES.md
  as agent-found rows here.
- An owner review like 2026-09-13 must produce rows here AND fixes
  in the app — never fixes without rows (rows are the learning).
| 2026-09-13 | e062 | history in UTC + `fresh NaNd ago` on e058 card | owner (screenshot) | — | history bypassed local-time helper; double-Z on ISO timestamps; fixed + UX §11 time law |
| 2026-09-13 | e062 | history toggle selects text (mobile web-search popup) + opens slowly | owner | — | toggle was a div (not a button) + every tap re-rendered the whole board; fixed: no-select + targeted in-place toggle |
| 2026-09-13 | e062 | card shows `next:` twice (focus + ladder lines ungrouped) | owner | — | loop text rendered as loose lines; fixed: single grouped NEXT (focus · ladder · note); credit game written into DIRECTIVES |
| 2026-09-15 | wander | capture starved 2 days: legs claim claim.json every 30min and never delete, so the cron's shared-file skip never fired | wander run134 | ~48 | mechanism fix, not a third shelf log: capture cron owns capture-claim.json now, never reads/deletes leg claims; legs delete claim.json when done |
| 2026-09-15 | wander | shelf bare 3rd review (run133-135) but run134 claim-split had no capture window since to prove itself — unverified, not failed | wander run135 | ~72 | no 4th shelf log: next 11:15/16:15 window is the verdict (shots land = split worked; still bare = debug capture.sh directly + beat wander-camera-dead) |
| 2026-09-15 | e059 | phone shot shows LIVE badge over "(data mixed 2026-09-11→2026-09-15)" while server line already said "16 current, 14 lagging" — client JS overwrote honest SSR with vague mixed range, stale coins unnamed | wander run153 | ~5 | SSR fixed in prior leg but CSR pulse() never mirrored it; fixed: mode-thru helper + stale-mark in pulse/verdict/alerts JS, bake-verify both paints, e2e PASS 9681fe0 |
| 2026-09-15 | wander | run155 logged all-7-blank camera fault, but 6/7 PNGs render full app content — checks.txt FAILED measures capture exit, not pixels | wander run156 | ~1 | eyes review of 11:20 shots corrected the verdict; only e063 shows connecting-spinner (capture-side JS wait, app e2e PASS d975ac3); fix ideas banked e065 run156 (content-assert + findings fix-ts) |
| 2026-09-15 | e058 | 360px shot: fixed thumbbar wraps to 2 rows (~150px+) but body padding-bottom is 124px — last table rows hide under the bar | wander run160 | ~9 | DIES IN WRITING per 2-wander rule (2nd sighting, tree dirty = hands-off): exact fix = `.thumbbar{flex-wrap:nowrap;overflow-x:auto}` one-row scroll, or 190px padding media query; ship when tree clean |
| 2026-09-15 | e059 | mixed data_through across coins (2nd sighting) | wander run160 | ~29 | BECAME DATA per 2-wander rule: output/tvl.json single-date TVL+P/TVL 27/30 from free llama endpoints + per-coin stale marks already live; no third log |
| 2026-09-15 | e059 | mixed data_through tripwire fires 3rd time while page discloses (freshness table + per-row stale column) — detector measures data, not disclosure | wander run162 | ~5 | KILLED IN WRITING per never-a-third-log: wander.sh tripwire now disclosure-aware (fires only when lagging prose/table disclosure missing), verified False on live page; P/TVL column re-wired onto sibling table-first rewrite after mid-leg file collision, e2e PASS 7905b78 |
| 2026-09-15 | e059 | mid-leg file collision: parallel writer rewrote inject.py+page.html (table-first) between run162 read and commit — first TVL wiring silently dropped from staged file | run162 self | ~0 | merged TVL join onto the new file, re-ran inject, e2e PASS, committed both in one same-track commit 7905b78; rule: re-read files modified after your last read before git add on shared tracks |
| 2026-09-15 | e058 | served uncommitted table migration (pulse line -> ppulse table) dropped e2e-contract phrase "held 24h": server restarted 21:48:27Z onto 21:48:16Z half-edit, e2e FAIL, owner card showed richer but uncontracted numbers | leg run163 | ~0 | rolled back to BEST 823d136 (e2e PASS, dirty:false), migration preserved at /tmp/e058-migration-run163.patch for owning leg to re-apply with e2e string updated; rule: never restart a served app onto a dirty tree without e2e PASS first |
| 2026-09-15 | e060 | phone shot: radar table 4th column header+values truncated at right edge ("c...", "-...") with no visible expand affordance on first paint | wander run163 | ~5 | first sighting: verify whether .twrap inner-scroll reveals it on swipe; if not, add sticky first-col or col-toggle before 2nd sighting (dies-in-writing or becomes-data per 2-wander rule) |
| 2026-09-15 | e060 | phone shot: radar table 4th column header+values truncated at right edge (2nd sighting, same as run163) | wander run164 | ~30 | DIES IN WRITING per 2-wander rule: table ships `.twrap{overflow:auto}` + sticky first col + min-width 640px, so the cut column is revealed by inner-swipe by design (hard rule: tables scroll inside); no code change, no third log |
