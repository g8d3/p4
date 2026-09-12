# e061 — DEPLOYED (rung 2, 2026-09-12)

Smallest playable slice demo, static, fail-closed (no funds, no chain).

## Rung-2 evidence

- Live URL (tailnet): `http://100.102.52.59:8321/` — curl 200 via tailnet,
  verified 2026-09-12 (~09:00 UTC leg). Binds `0.0.0.0:8321`.
- Survives reboot: `@reboot cd .../e061-game-launchpad-suite/demo &&
  python3 -m http.server 8321 --bind 0.0.0.0` present in crontab.
- Freshness / stale-badge: static demo, no live data to go stale.
  `status.json` explicitly fail-closed (`pair: none deployed`,
  `disableReason: pair not deployed / chain not anvil`), served live
  at `/status.json`. Server log shows periodic tailnet GET 200s.
- Secrets: none in repo (static HTML only; grep clean).

## What it proves

Suite slice spec (SPEC.md) is servable over the tailnet to the owner;
token action stays disabled until e052 anvil-fork is ready.
Next rung (TESTED): e2e click-path of win-screen → disabled-buy +
monitored errors, or paper-tracked slice event.
