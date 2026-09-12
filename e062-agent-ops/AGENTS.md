# e062 — Agent Ops (fleet nervous system)

Agents work in bursts; continuity comes from state, not stamina. This
experiment is the shared infrastructure that keeps every track moving
toward DONE without a human watching.

## DONE ladder (every app climbs the same rungs)

1. **WORKING** — runs locally, endpoints verified with curl, no secrets.
2. **DEPLOYED** — live URL (via gateway, P2 decision), survives reboot
   (cron/systemd + heartbeat), data fresh or explicitly stale-badged.
3. **TESTED** — e2e or paper-tracked; errors monitored, not silent.
4. **ANNOUNCED** — owner notified (ntfy) with URL + what it proves.
5. **MONETIZED** — separate gate, only after usage: billing, referrals,
   API tiers. Never before.

Rungs 1–4 are the agents' job, nonstop. Rung 5 is a business decision
with the owner.

## Components

- `ops.db` (SQLite, this dir): `events(ts, track, kind, summary, dedup_key)`,
  `heartbeats(track, ts, status, note)`, `rungs(track, rung, ts, url, note)`.
- `bin/ops.py`: `init`, `emit`, `beat`, `stale`, `status`, `promote`.
- Contracts: each track emits only new-information events (dedup_key +
  cooldown, same lesson as e058 alert.py). Humans get conclusions only.
- Staleness scan: any track silent > 2× its expected cadence → event
  `track-stale` → wake a builder or propose kill.

## Conventions

- No secrets in repo (env only). Every writer is a cron per CRON.md rules.
- Status lines: BUILDING / BLOCKED / PROVEN + numbers. Nothing else.

## Runner (forever legs) + autonomy

- `bin/runner.sh` + `RUNNER_PROMPT.md`: bounded dispatcher leg via
  `pi --print` (verified working headless). Reads ops state, executes
  ONLY approved proposals, revives one stale track or advances lowest
  rung, beats, exits. Install (owner call — spends quota 24/7):
  `*/30 * * * * .../bin/runner.sh >> .../runner.log 2>&1`.
- `SPEND.md`: T0 free / T1 ≤$50 auto+logged / T2 propose-and-wait.
  No KYC bypass, no ToS farming, one wallet per blast radius.
- `ops.py propose|decide|proposals`: async approval queue (verified
  round-trip). Green/yellow/red service lists in SPEND.md.

## URL convention

Public board/app URLs use the Tailscale IP (`http://100.102.52.59:PORT`),
never 127.0.0.1 — owner visits from phone/laptop over the tailnet.
All app servers bind 0.0.0.0.
