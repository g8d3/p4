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
- SCORE: resolved=0/0 (thin-data, first 24h outcomes land ~2026-09-14, 10 pending) — next leg resolves or reports pending count.
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
