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
- SCORE: resolved=0/0 (thin-data, first 24h outcomes land ~2026-09-14 05:33Z, 5 pending) — next leg resolves or reports pending count.
- EARLY-READ (run #42, FREE probe, no fetch): app.py early_read() compares
  latest worthy entries vs current rotation.json prices; card verdict +
  one-line expand + /api/paper carry per-call detail. Read 2026-09-13
  ~09:35Z: 1/4 up, avg -10.5% at 4.0h, best CATFLIGHT +0.8%
  (PURRLTR -6.1%, Stunk -15.6%, FRONTIER -21.1%). Worthy pings still COLD
  intraday — do not chase; canonical 24h grade still pending (~20h).
- KILL RULE (owner-blessed 2026-09-12): no signal in 2 weeks → kill track.
  Degrade 2 legs running → demote to PAPER (already PAPER, so → kill review).
