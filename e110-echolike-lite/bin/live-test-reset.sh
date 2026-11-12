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
# Two kinds of leftovers: the claim window itself, and the tenants a test suite
# claims and never uses (no capture). A tenant with captures is NEVER touched —
# that is somebody's inbox.
wrangler d1 execute echolike-inbox --remote --command \
  "DELETE FROM claims;
   DELETE FROM devices WHERE user_id IN (
     SELECT d.user_id FROM devices d
      WHERE NOT EXISTS (SELECT 1 FROM likes l WHERE l.user_id = d.user_id));
   DELETE FROM devices WHERE user_id IN (SELECT id FROM users WHERE created_at < datetime('now','-2 hours'));
   -- Test tenants keep devices behind until the 50-per-IP cap answers 409. A real
   -- inbox has captures and, usually, a phone or two; a test one has a handful.
   DELETE FROM devices WHERE user_id IN (
     SELECT d.user_id FROM devices d
      WHERE (SELECT COUNT(*) FROM likes l WHERE l.user_id = d.user_id) < 5
        AND NOT EXISTS (SELECT 1 FROM account_tenants t WHERE t.user_id = d.user_id));" \
  2>&1 | grep -E "rows_written|error" | head -4
echo "claim window cleared; the live tests can claim again"
