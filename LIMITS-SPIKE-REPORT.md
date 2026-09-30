# LIMITS Spike Report (2026-09-29)

Charter: repo-root `LIMITS.md` (6 standing targets, each a future business) +
wire it to the e082 loop + first research spike (L4 headed browser) + proof.

## Charter location

- `LIMITS.md` — repo root. 6 open checkboxes `[limits-l1..l6]`, loop-parseable
  format (`- [ ] [limits-lN] title`), each with ToS guardrail, agent-side vs
  human-tap split, acceptance proof, business (who pays / for what / ~$/mo).
- `log/limits.log` — repo root log dir, append-only run diary.
- This report — repo root (`LIMITS-SPIKE-REPORT.md`).

## Loop proof (tick id: cycle 1172)

Smallest change, all rules in needs.json (`limits_every_n_ticks=4`,
`limits_doc`), never hardcoded:

- `server/app.py`: `limits_open_items()` parses open checkboxes (checked =
  done, skipped); `backlog_current()` diverts every 4th tick to an open
  LIMITS item, rotating; `collect_limits_evidence()` runs the item's smallest
  shippable slice = a read-only local probe (no accounts, no logins, no
  posts, no payments), logged to `evidence.jsonl`; `/api/backlog` serves
  3 e083 + 6 LIMITS items.
- `test/check.sh`: limits rules assert + fixtures (6 parsed, diversion,
  l4 probe green, fixture row removed) + live ticks to the next
  4-divisible cycle + evidence assert + receipt assert + hands
  side-effect cleanup. Suite: **PASS** end to end.
- Live tick: **cycle 1172 consumed `limits-l5`** —
  `L5 domain path live: 5 RDAP-available names shortlisted in DOMAINS.md,
  zero agent payments issued` (rows=5, ok=true); tick notes carry the item;
  gaps/drafts hands filed en route were owner-cleaned.
- Restart: e082 exact PID 1508016 → 1535136 via `bin/serve.sh` (PID read
  from `ss -tlnp`). Daemon alive (pid 1317232), ticking every 60s — every
  4th tick now works a LIMITS item.
- Seat review (`?agent=limits-seat-pass`): board To-do card shows the live
  item + last proof; every card keeps a user action
  (`e082-forever-harness/seat-limits-proof.png`).

## L4 measurements (headed/Xvfb upgrade, THIS box)

Recipe that works: `agent-browser close` first (daemon holds one mode;
`--headed` is silently ignored while headless), then prefix EVERY call with
`DISPLAY=:99` (Xvfb :99 pre-existing, PID 974655 — no new Xvfb needed).

| Test (bot.sannysoft.com) | Headless | Headed (Xvfb :99) |
|---|---|---|
| WebDriver (New) | present (FAILED) | present (**STILL FAILED**) |
| WebGL renderer | SwiftShader (headless tell) | **Mesa llvmpipe (tell gone)** |
| Window chrome | none | real (outer 1004×1050) |
| Rest of suite | ok | ok |

Conclusion: headed removes the GPU + window tells but CANNOT kill
`navigator.webdriver` — agent-browser drives via CDP in both modes.
`BROWSER-CAPABILITY.md` updated with recipe + table; shot
`.growth-shots/sanny-headed-xvfb.png`. L4 stays OPEN; next slice is a
Camoufox (non-CDP) comparison per e020. No accounts created, no logins
bypassed, no posts made.

## WHAT I STILL DISTRUST

1. **Headed daemon is opt-in per call.** Any agent forgetting `DISPLAY=:99`
   or opening while the daemon is headless silently measures headless while
   believing headed. The recipe relies on discipline, not a guard.
2. **Limits probes verify preconditions, not progress.** Each tick re-checks
   the same static facts (files exist, TOKEN set) — the items can never
   close by ticking alone. Real closure needs owner taps (L1 Create, L5
   checkout) or a built asset (L2 pack, L4 Camoufox run). The loop currently
   has no "stalled limits item" escalation.
3. **Rotation math drifts the e083 cadence.** Diverting every 4th tick shifts
   which e083 slice lands on which cycle; any future fixture pinning an
   exact cycle→slice mapping will break. `/api/backlog` current-id is the
   stable contract, not cycle arithmetic.
4. **Daemon interleaving in check.sh.** The 60s daemon can tick between suite
   ticks; the limits proof reads the evidence row by cycle id (robust), but
   the gate assert on a moving last-cycle is inherently racy — left as
   evidence-row proof deliberately.
5. **Hands side-effects during limits ticks.** Proving a LIMITS tick fires up
   to 4 real ticks, each of which may file gaps/drafts via hands. The suite
   snapshots + cleans, but a daemon tick racing the suite window could leave
   one real gap open. Next run should assert zero-diff, not just clean.
6. **L4's real fix is unproven.** Mesa llvmpipe is still obviously virtual
   (LLVM software rasterizer) to a strict detector — we removed the
   *headless* tell, not the *automation* tell. Do not sell the Bot-Wall
   Audit until Camoufox scores webdriver=false on this box.
