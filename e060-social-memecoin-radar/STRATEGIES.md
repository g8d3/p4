# e060 STRATEGIES — worthy-ping ladder (owner: cheapest/free, Dexscreener-only)

Every strategy walks HYPOTHESIS → BACKTEST → PAPER → PROPOSE (never skip).
N<20 resolved = THIN: never propose real money on THIN.

## WORTHY-1: heat + volume + trade-speed rotation ping (ACTIVE, PAPER)

- HYPOTHESIS (1 line): tokens with paid boost attention AND live on-chain
  velocity keep running 24h later; edge = attention + velocity combined,
  invalidation = hit-rate ≤50% over N≥20 resolved.
- PARAMS: heat ≥ 80 (heat = score + 5·log10(txns+1) + min(|chg24h|,150)/10),
  vol_h24 ≥ $500k, txns_h24 ≥ 10k. Universe = Dexscreener top-15 boosts.
- BACKTEST: none yet — no historical price series on the free tier
  (Dexscreener public API is current-price only). THIN by construction.
- PAPER (live 2026-09-13): bin/paper_snapshot.py logs top-10 + entry
  priceUsd + worthy flag daily (cron 07:17 UTC); bin/paper_resolve.py
  re-fetches 24h later, hit = price up; paper/score.json holds the
  hit-rate; card shows it on first paint + /api/paper. Watch-only, never
  a position.
- SCORE: resolved=0/0 (thin-data, first 24h outcomes land ~2026-09-14 05:33Z, 18 pending) — run #72 resolver re-run: 0 new, Sep-12 snapshots ungradeable (pre-priceUsd, no entry) — next leg grades or reports ballot.
- EARLY-READ (run #42, FREE probe, no fetch): app.py early_read() compares
  latest worthy entries vs current rotation.json prices; card verdict +
  one-line expand + /api/paper carry per-call detail. Read 2026-09-13
  ~09:35Z: 1/4 up, avg -10.5% at 4.0h, best CATFLIGHT +0.8%
  (PURRLTR -6.1%, Stunk -15.6%, FRONTIER -21.1%). Worthy pings still COLD
  intraday — do not chase; canonical 24h grade still pending (~20h).
- KILL RULE (owner-blessed 2026-09-12): no signal in 2 weeks → kill track.
  Degrade 2 legs running → demote to PAPER (already PAPER, so → kill review).
- RUN #46 PROBE (FREE, local files only, no fetch): tested WORTHY-2
  dump-filter (WORTHY-1 + chg24h > -80%) on 2026-09-13 entries — REJECTED,
  not shipped: keeps 1/5 (Stunk, -20% drift) and drops CATFLIGHT (+0.6%,
  the only green). Overfit on N=5; WORTHY-1 stays PAPER unchanged.
  Shipped instead: live grade-countdown in pulse ("first grade ~18h"
  from oldest worthy-with-price snapshot) + plain-words explainer
  ("Your radar sorts with one tap below"). Early 2026-09-13 ~11:35Z:
  1/4 up, avg -12.2% at 6.0h, best CATFLIGHT +0.6% — still COLD intraday.
- RUN #47 FIX (FREE, local only, no fetch): JS was discarding the live
  countdown after load (server "first grade ~18h" → vague "<24h").
  /api/paper now carries grade_cd and the pulse, verdict suffix, and
  Copy slip all keep it ("5 calls resolving (first grade ~18h)").
  Early 2026-09-13 ~12:00Z: 1/4 up, avg -10.5% at 6.5h, best
  CATFLIGHT +0.6% — still COLD intraday; canonical grade still pending.
- RUN #50 FIX+POWER (FREE, local only, no fetch): top verdict was
  jargon-dense (chain + heat + vol + chg in one breath) and the day's
  biggest intraday move sat buried in the early expand. Verdict now
  leads plain ("Top now: X — worth a look") + breakout ping: best
  early move >= +20% surfaces as "🔥 SYM up +N% since its call" in
  the one-line verdict, paper suffix, copy slip, and early summary
  (server + JS; detail stays behind the expand). WORTHY-1 rule
  unchanged, still PAPER. Early 2026-09-13 ~13:35Z: 1/5 up at ~1.2h,
  BLAST +30.0% Breakout LIVE while the group avg sits near flat —
  exactly the case the ping is for; canonical 24h grade ~16h out.
- RUN #52 FIX (FREE, local only, no fetch): first paint could show STALE with no thumb-zone retry (cache TTL 5m, bg refresh lands seconds later — owner saw STALE 30m with nothing to tap). Thumbbar gains Refresh (two-phase: immediate re-fetch + second pass after 7s to catch the bg refresh). WORTHY-1 unchanged, still PAPER. Early 2026-09-13 ~14:35Z: 2/5 up, avg +13.4% at 2.2h, best Stunk +51.1% + BLAST +25.3% — two breakouts live; canonical 24h grade ~15h out (10 pending, 0 resolved).
- RUN #51 POWER (FREE, local only, no fetch): early expand was a bare
  number (SYM +N%) with no tap to act. early_read now carries entry +
  cur + pairUrl per call; expand renders "SYM +N% entry X \u2192 now Y"
  + trades tap (server + JS, backward-compatible). WORTHY-1 unchanged,
  still PAPER. Early 2026-09-13 ~14:05Z: 2/5 up, avg +13.4% at 1.7h,
  best Stunk +51.1% + BLAST +25.3% — two breakouts live; canonical
  24h grade ~16h out.
- RUN #53 FIX+POWER (FREE, no fetch): first paint STILL greeted STALE after 15+ idle min (refresh was request-triggered only; /health hits never rebuild). Server now self-refreshes every 60s + warms cache at boot, so the card opens LIVE with no tap needed. Snapshot now logs the full top-15 universe (was top-10) so each daily snapshot banks more worthy calls toward N>=20 resolved. WORTHY-1 unchanged, still PAPER. Early 2026-09-13 ~15:05Z: 1/5 up, avg -8.0% at 2.7h, best BLAST +17.0% — cooling intraday; canonical 24h grade ~14h out (10 pending, 0 resolved, blocked-on-time).
- RUN #59 FIX (FREE, local only, no fetch): card flashed STALE—restart after JS load even while LIVE (sample 2m) with code untouched — /api/version latest was git-log on the whole track dir, so every paper snapshot commit (dd0bd34) faked a stale badge. Scope now code-only (app.py+bin/+tests/, same as dirty check); data commits no longer scare the owner. WORTHY-1 unchanged, still PAPER. Early 2026-09-13 ~17:35Z: 3/6 up, avg -25.0% at 2.5h, best CATFLIGHT +1.8% — cooling intraday; canonical 24h grade ~12h out (18 pending, 0 resolved, blocked-on-time).
- RUN #60 PROBE (FREE, local only, no fetch): re-tested dump-drag on a
  bigger early window — 10 worthy-with-price entries (3 snapshots) vs live
  prices. DUMPED (entry chg24 <= -50): 4/5 up, avg -4.1%. REST: 0/5 up,
  avg -69.4%. Dump-filter REJECTED again (dumps bounce +1-2%, pumps crash).
  NEW CANDIDATE WORTHY-2c (HYPOTHESIS, THIN): upside-cap — exclude entries
  with chg24 > +200% (BLAST +5371/+5604, Mizzy +499 = 0/3, avg -75.3%;
  rest 4/7 up avg -20.2%). Mean-reversion, not momentum. N=10 intraday,
  THIN — needs N>=20 resolved 24h before any rule change. WORTHY-1 stays
  PAPER unchanged. SHIPPED (display-only): top verdict now reads
  "hot but falling — watch only" when top worthy chg24 <= -50 (server +
  JS + copy-slip FALLING flag), dumped rows carry a falling marker —
  owner no longer sees "worth a look" on a -66% crasher.
- RUN #61 FIX+POWER (FREE, local only, no fetch): mirror guard for the
  other tail — top verdict said "worth a look" on BATONIUS +522%, a
  WORTHY-2c upside-cap setup (chg>+200 0/3, avg -75.3%). Top verdict now
  reads "hot but pumped — watch only" when top worthy chg24 >= +200
  (server + JS + copy-slip PUMPED flag), pumped rows carry a warning
  marker. WORTHY-1 rule unchanged, still PAPER; WORTHY-2c still THIN
  (needs N>=20 resolved). Early 2026-09-13 ~18:30Z: 2/5 up, avg -39.2%
  at 3.5h, best CATFLIGHT +3.7% — cooling intraday; canonical 24h grade
  ~11h out (18 pending, 0 resolved, blocked-on-time).
- RUN #64 FIX+POWER (FREE, local only, no fetch): verdict still lured with
  "hot" on disqualified tops (BATONIUS +421% "hot but pumped"). Guard words
  now "pumped — not a buy, watch only" / "falling — not a buy, watch only"
  (server + JS, copy-slip flags unchanged) — owner no longer sees "hot" on
  a coin he's told not to touch. POWER: WORTHY-2c upside-cap now runs as a
  live SHADOW on the intraday window — early_read carries capped =
  ex-pumped (entry chg24>+200 out), surfaced one-line in verdict, /api/paper
  early.capped, and JS suffix (server + JS, display-only, canonical rule
  unchanged, still PAPER). Shadow 2026-09-13 ~20:00Z: full 1/4 up avg
  -57.9% vs capped 1/2 up avg -29.0% (BLAST +5604/Mizzy +499 excluded, both
  deep red) — cap halves the bleed intraday, still COLD, still THIN (needs
  N>=20 resolved 24h). Canonical 24h grade ~10h out (18 pending, 0 resolved,
  blocked-on-time).
- RUN #69 DATA+POWER (FREE, GeckoTerminal no-key, T1 $0): STUCK RULE fired —
  worthy-hit-rate 0/0 flat 4 legs, so this leg ADDS free data instead of
  re-grading. NEW bin/pools_backfill.py resolves every pending worthy token
  to its top GeckoTerminal pool (chain map solana/robinhood, 3s pacing,
  skip-fresh 24h, idempotent) → paper/pools.json {token: network/pool/
  pool_addr/px_usd/ts}. Coverage 2026-09-13 ~22:35Z: 9/9 pools (7 solana +
  2 robinhood — GeckoTerminal knows the robinhood network). Resolver run
  same leg: resolved=0 pending=18 new=0 (first grade ~7h, blocked-on-time).
  Next: resolver pool-OHLCV fallback so vanished tokens still grade (fewer
  dropped outcomes, faster N>=20). POWER (saved data put to work):
  early_read now carries tracked = usable/priced ("4/8") + tracked_partial,
  surfaced one-line in the verdict + /api/paper + JS suffix ("4/8 still
  tracked") — owner sees half today's calls already left the boost universe
  with no extra tap. Mizzy -99.5% VERIFIED REAL (direct Dexscreener:
  0.000002307 vs entry 0.0004337; CATFLIGHT 0.000002287 — both dead
  pump.fun dust at the same floor, not a price bug). WORTHY-1 still PAPER,
  WORTHY-2c still THIN shadow.
- RUN #70 FIX+POWER (FREE, GeckoTerminal no-key, T1 $0): table header said
  "traders" but every cell is a "pair ↗" link — relabeled to "pair"
  (server + JS bundle, one word, owner no longer misled). POWER: the
  run-#69 focus item ships — resolver pool-OHLCV fallback is LIVE in
  bin/paper_resolve.py. Vanished tokens no longer drop: Dexscreener
  first, else cached-pool hourly candle at entry+24h (gecko-ohlcv), else
  pool spot (gecko-spot); outcomes carry src so the card can say how it
  graded. PROVEN this leg on live data (read-only probes, no outcomes
  written): backdated-12h candle pick px=0.00287 at-or-before target,
  forced-dex-fail path returns gecko-ohlcv px=0.000718. Resolver run same
  leg: resolved=0 pending=18 new=0 gecko_fb=0 (first grade ~7h,
  blocked-on-time — nothing due yet, fallback waits for its first real
  grade). WORTHY-1 still PAPER, WORTHY-2c still THIN shadow.
- RUN #71 FIX (FREE, local only, no fetch): grade source surfaced on card
  (focus half shipped). Pulse now reads "18 worthy calls resolving (first
  grade ~6h) · grades via live, backup 9/9" (grade_src_line: outcomes src
  tally once resolved, else pools.json cache count); early moves labeled
  "via live" in summary + per-call rows + /api/paper (px_src + px_age +
  per-detail src). Resolver re-run: 0 new, 18 pending (blocked-on-time,
  first grade ~6h). e2e PASS local+tailnet, d26eb44 live running==latest.
  SCORE: resolved=0/0 (delta 0 vs run #70) — FIX, not advance.
- RUN #72 FIX+POWER (FREE, local only, no fetch): resolver re-run 0 new /
  18 pending — Sep-12 pair ungradeable by construction (pre-priceUsd,
  no entry price, skipped not dropped) + Sep-13 trio all <24h; first
  canonical hit-rate lands ~2026-09-14 05:33Z (blocked-on-time). POWER:
  per-call ballot ships (ISSUES #2+#3) — /api/paper pending_calls +
  server <details id=ballot> + JS refresh: one line per pending snapshot
  (coins, called Xh ago, grades in Yh). Verdict now LEADS with action
  state (server + JS + copy slip: "WATCH — Top now: …" / "COLD — …",
  breakout flips COLD→WATCH) and the lure word stays buried — BUY never
  emitted on PAPER (watch-only, never a position). WORTHY-1 unchanged,
  still PAPER. Early 2026-09-14 ~00:40Z: 0/3 up, avg -84.5% at 9.6h,
  best BLAST -76.5% — COLD intraday, ex-pumped 0/1, 3/8 still tracked.
- Run #87: FIRST GRADES 1/5 (20.0%, CATFLIGHT +2.6% HIT via dexscreener; Stunk -99.5%, CATAI -76.5%, FRONTIER -39.4%, PURRLTR -17.4% miss). N=5 THIN, stays PAPER. Early ex-pump decay confirmed — worthy bar may need lift next leg.

## Worthy-bar autopsy (run #88)
- 5 resolved, 1/5 = 20.0% (CATFLIGHT +2.6% HIT; Stunk -99.5%, FRONTIER -39.4%, PURRLTR -17.4%, CATAI -76.5% miss). All 5 were worthy=True — the bar as-is lets losers through.
- Shadow candidate (PAPER-tracked, N=2 THIN, never live on THIN): txns>=30k & vol>=1M keeps CATFLIGHT + Stunk only = 1/2 = 50%. Served on card as `stricter bar 50% (1/2, trying)` via /api/paper shadow. Live bar unchanged until shadow N>=20.
- Run #90: resolved still 5 (1/5=20.0% flat — Sep-13 batch ungradable: 5 symbols no entry price, skipped not dropped). Today's snapshot banked 11 worthy + 7 shadow-rule candidates (all with entry prices, resolve ~Sep-15). Pending 5→16. e2e PASS. Stays PAPER (live 20% + shadow 50% both THIN). Next: grow shadow N to 20 (7 in pipeline).
- Run #91: resolved still 5 (1/5=20.0% flat — Sep-14 batch too young to grade). Snapshot banked today's 15 worthy (stale=False), pending 16→28. Shadow still n=2 (50% THIN). e2e not re-run (no code change; :8323 running==latest c9c63bc). Stays PAPER. Next: keep banking daily snapshots toward shadow N=20; first big grade wave ~Sep-15.
- Run #99: SHADOW2 live (PAPER-only looser bar txns>=10k & vol>=300k, run #98 idea shipped): shadow2 N=5 (1/5=20.0%) on same 5 resolved vs strict N=2 (50%). Served on card as `looser bar 20.0% (1/5, trying)` beside stricter via /api/paper shadow2. Restarted :8323 running==latest. Stays PAPER (both THIN). Next: bank daily snapshots toward shadow2 N=20; first big grade wave ~Sep-15.
- Run #104: resolved still 6 (1/6=16.7% flat — today's batch too young, next grade wave ~Sep-15). Snapshot banked 15 calls (stale=False), pending 123→136 (+13 toward shadow2 20). Card live with no restart (pending 136, `grades in ~59m`, sticky thumbbar verified in served HTML), running==latest 75071dc. Stays PAPER (live 16.7% + shadow2 16.7% both THIN). Next: keep banking toward shadow2 N=20; big grade wave ~Sep-15.
- Run #121: resolved still 9 (3/9=33.3% flat — resolver re-run new=0, today's batch too young; pools backfill 18/25 cached so fewer future grades drop). Stays PAPER (THIN). Next: grade wave lands today; then push resolved toward 20 bar.
- Run #124: resolved still 9 (3/9=33.3% flat — resolver re-run new=0, write skipped, 175 pending too young; shadow strict 3/5=60% THIN + loose 3/9=33.3% THIN). Card live with no restart (grade line + backup 22 pools + both bars in served HTML, phone-verified), running==latest 4ea7482. Stays PAPER (THIN). Next: grade wave lands as 175 age past 24h; push resolved toward 20 bar.
- Run #126: resolved still 9 (3/9=33.3% flat — resolver re-run new=0, 175 pending too young; shadow strict 3/5=60% THIN + loose 3/9=33.3% THIN). Today's snapshot banked (22nd, 15 calls stale=False, 4 strict-rule candidates toward shadow N=20). Card live with no restart, running==latest 4ea7482. Stays PAPER (THIN). Next: grade wave lands as backlog ages past 24h; push resolved toward 20 bar.
- Run #128: snapshot banked 15 calls, pending 191->199 (+8), resolves 0 new, 3/9=33.3% flat (shadow 3/5=60% THIN) — stays PAPER. UI: phone-curled, no new friction. e2e implied, running==latest 4ea7482. Next: grow shadow 60pc toward 20 via backfill-replay; grades land through 09-16.
- Run #129: snapshot banked 15 calls, pending 199->207 (+8, same bank-vs-grade clock skew as run128), resolves 0 new, 3/9=33.3% flat (shadow 3/5=60% THIN) — stays PAPER. UI: phone-curled, legend already behind one-line summary, no fix. running==latest 4ea7482. Next: grow shadow 60pc toward 20; grades land through 09-16.
