#!/usr/bin/env bash
# bin/live-test-reset.sh — clear the hosted inbox's claim counters before a test run.
#
# The live tests claim tenants from this machine; the production guard caps claims
# per IP per hour (20) and devices per IP (50), and a suite that runs twice reaches
# it. This clears the rolling claim window so the tests measure the product, not
# their own footprint. It weakens abuse protection for about a minute: dev only.
set -euo pipefail
cd "$(dirname "$0")/../inbox-worker"
export CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-${CLOUDFLARE_FOCALIS_API_KEY:-}}"
[ -n "$CLOUDFLARE_API_TOKEN" ] || { echo "no Cloudflare token in the environment"; exit 1; }
wrangler d1 execute echolike-inbox --remote --command \
  "DELETE FROM claims; DELETE FROM devices WHERE user_id IN (SELECT id FROM users WHERE created_at < datetime('now','-2 hours'));" \
  2>&1 | grep -E "rows_written|error" | head -4
echo "claim window cleared; the live tests can claim again"
