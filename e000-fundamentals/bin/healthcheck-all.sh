#!/bin/bash
# healthcheck-all.sh — single cron entry that fans out to every per-app probe.
# Replaces 7 identical */15 crontab lines. Each per-app script is unchanged:
# silent on success, logs + beats the ops bus on failure. T0 free.
# Cron: */15 * * * * .../e000-fundamentals/bin/healthcheck-all.sh >> .../healthcheck-all.log 2>&1
# Probes (port -> script):
#   :8320 e058 funding scanner | :8324 e059 valuations (static) | :8323 e060 memecoin radar
#   :8321 e061 game launchpad | :8322 e062 agent ops (self-heals) | :8325 e063 fleet ui
#   :8326 e067 sys panel (self-heals)
set -uo pipefail
P4="$HOME/code/p4"
for hc in \
  e058-funding-scanner/bin/healthcheck.sh \
  e059-crypto-valuations/bin/healthcheck.sh \
  e060-social-memecoin-radar/bin/healthcheck.sh \
  e061-game-launchpad-suite/bin/healthcheck.sh \
  e062-agent-ops/bin/healthcheck.sh \
  e063-fleet-ui/bin/healthcheck.sh \
  e067-sys-panel/bin/healthcheck.sh ; do
  "$P4/$hc" || true
done
