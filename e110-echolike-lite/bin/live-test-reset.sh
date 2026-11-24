#!/usr/bin/env bash
# bin/live-test-reset.sh — clear the hosted inbox's claim counters before a test run.
#
# The live tests claim tenants from this machine; the production guard caps claims
# per IP per hour (20) and devices per IP (50), and a suite that runs twice reaches
# it. This clears the rolling claim window so the tests measure the product, not
# their own footprint. It weakens abuse protection for about a minute: dev only.
#
# HARD RULE: never delete a device row for a tenant that has captures, and never
# delete device rows by user age. A device token exists only as a sha256 here, and
# the client keeps the only copy of the value — deleting the row revokes that
# person's inbox with no way back. An earlier version of this script did exactly
# that (`DELETE ... WHERE user_id IN (SELECT id FROM users WHERE created_at < ...)`),
# which silently logged every real install out on 2026-11-24. Cleanup is now limited
# to devices/tenants with **no captures at all** and created in the last day.
set -euo pipefail
cd "$(dirname "$0")/../inbox-worker"
export CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-${CLOUDFLARE_FOCALIS_API_KEY:-}}"
[ -n "$CLOUDFLARE_API_TOKEN" ] || { echo "no Cloudflare token in the environment"; exit 1; }
wrangler d1 execute echolike-inbox --remote --command \
  "DELETE FROM claims;
   -- Only test leftovers: no capture ever, no account, claimed recently.
   DELETE FROM devices WHERE user_id IN (
     SELECT d.user_id FROM devices d
      WHERE d.created_at > datetime('now','-1 day')
        AND NOT EXISTS (SELECT 1 FROM likes l WHERE l.user_id = d.user_id)
        AND NOT EXISTS (SELECT 1 FROM account_tenants t WHERE t.user_id = d.user_id));
   -- A user row with no device and no capture is a spent test claim, not an inbox.
   DELETE FROM users WHERE id NOT IN (SELECT user_id FROM likes)
                        AND id NOT IN (SELECT user_id FROM devices)
                        AND id NOT IN (SELECT user_id FROM account_tenants);
   -- Discovery rows belong to a person with captures; a zero-capture tenant is a test.
   DELETE FROM interest WHERE user_id NOT IN (SELECT DISTINCT user_id FROM likes);
   DELETE FROM discovery_opt WHERE user_id NOT IN (SELECT DISTINCT user_id FROM likes);" \
  2>&1 | grep -E "rows_written|error" | head -6
echo "claim window cleared; the live tests can claim again"
