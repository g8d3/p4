# VERDICT — Phase 1 network-access proof (2026-10-05)

All claims below cite a saved file + URL + date. No claim without evidence.

## Which pipes work today

| Pipe | Status | Evidence |
|---|---|---|
| `tinyfish search query` | WORKS — live index, 7 ranked results for "solana launchpad september 2026", exit 0 | `evidence/tinyfish-probe.md` §1, 2026-10-05T14:54:49Z |
| `tinyfish fetch content get` (default JSON) | WORKS on normal SSR/marketing pages — full article text from `https://www.alchemii.io/blog/best-solana-launchpad-2026` and `https://madeonsol.com/compare-launchpads` (2026-10-05) | `evidence/tinyfish-probe.md` §2–§3 |
| `agent-browser` local Chromium + L1 stealth on static/SSR pages | WORKS — `https://example.com/` and `https://solana.com/news/solana-changelog-september-10-2026` render with readable snapshots (2026-10-05) | `evidence/browser-probe.md` §1, §3 |
| `agent-browser` on public X profiles (logged-out) | WORKS — `https://x.com/solana` renders bio ("The high performance network…", 4.2M Followers, Joined January 2018) + 3 recent posts with engagement counts (2026-10-05T14:56–14:58Z) | `evidence/x-probe.md` Attempt D |

## Which pipes are blocked / failed

| Pipe | Status | Evidence |
|---|---|---|
| `tinyfish fetch --pretty` body | HIDES the body (header only) — use default JSON for evidence, else you will falsely conclude "empty" | `evidence/tinyfish-probe.md` §2 note, 2026-10-05 |
| `agent-browser` on `https://www.alchemii.io/blog/best-solana-launchpad-2026` | FAILED — navigation timeout, empty snapshot, zero XHR captured (same URL `tinyfish fetch` reads fine). Pipes fail on different pages. | `evidence/browser-probe.md` §2, 2026-10-05 |
| X `/explore` (trends) via EITHER pipe | BLOCKED — both redirect to `https://x.com/i/jf/onboarding/web?redirect_after_login=%2Fexplore&mode=login` with login/JS-disabled boilerplate and empty render. No trends visible logged-out. | `evidence/x-probe.md` Attempts A + C, 2026-10-05 |
| Guessed status URL `https://x.com/solana/status/1965000000000000000` | INVALID TEST (ID was guessed) — `page_not_found` proves nothing; must not be cited as access evidence | `evidence/x-probe.md` Attempt B, 2026-10-05 |

## What this means for Phase 2 (X trend scout)

1. Trend discovery CANNOT use `/explore` — it is login-walled on both pipes today.
   The working path is: `tinyfish search` for topic coverage → `agent-browser`
   on PUBLIC profile/timeline URLs (`x.com/<handle>`) logged-out → quote posts
   verbatim with timestamps, like Attempt D.
2. Cross-verify every quantitative page (e.g. madeonsol.com comparison, "Last
   updated: September 2026") with a second pipe before locking the app idea —
   §2 of `browser-probe.md` proves one pipe alone gives false negatives.
3. Real status URLs must be harvested from rendered timelines, never guessed.

## What the user must verify ("eso está correcto" checklist)

- [ ] Open `https://x.com/solana` yourself and confirm the profile header in
  `evidence/x-probe.md` Attempt D matches what you see (bio, ~4.2M followers).
  Timelines move fast — the 3 quoted posts ("DGLD gold", "See you tomorrow 🇸🇬",
  "40 days till BREAKPOINT") are a 2026-10-05 snapshot, not a live feed.
- [ ] Open `https://madeonsol.com/compare-launchpads` and confirm the "Last
  updated: September 2026" lineup (Pump.fun vs Bonk.fun vs Moonit vs Bags vs
  Believe vs Boop.fun vs DAOs.fun) matches `evidence/tinyfish-probe.md` §3.
  In particular: Moonit maintenance page since ~Aug 2026 — is it back?
- [ ] Decide Phase 2 scope: public-profile scraping only (no login), or provide
  a logged-in session/cookies so `/explore` + search pages become testable?
  Without that, "X trends" = per-handle timelines + web-index coverage, honestly
  labeled as such.
- [ ] Confirm no app code starts before `DECISION.md` (per experiment AGENTS.md rules).

Method notes: e041 lessons applied — retry cap respected (no retry loops),
mirrors/second-pipe used instead of hammering blocks, stealth init-script from
`browser-extract` SKILL, `--pretty` fetch trap documented, zero lingering
chrome processes (`ps … | wc -l` → 0). Standing rules: no experiment servers
touched this turn (port 8769 in `needs.json` not started — no Phase 3 code yet),
so no server-URL/IP report applies.
