#!/usr/bin/env bash
# Mint one single-use portal invite and print the full registration link.
# Usage: ./bin/invite.sh   (no args; URL on stdout, nothing else)
set -euo pipefail
E028="$HOME/code/p4/e028-dsh-harness"
PUBLIC_HOST="${PUBLIC_HOST:-vuos-hcar5000mi.tail6918b0.ts.net}"
TS_PORTAL_PORT="${TS_PORTAL_PORT:-9446}"
USERS_FILE="${USERS_FILE:-$E028/portal/users.json}"
TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))')"
python3 - "$USERS_FILE" "$TOKEN" <<'EOF'
import json, sys, datetime
path, tok = sys.argv[1], sys.argv[2]
db = json.load(open(path))
db.setdefault("invites", []).append({
    "token": tok,
    "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "usedBy": None,
})
json.dump(db, open(path, "w"), indent=2)
EOF
chmod 600 "$USERS_FILE"
echo "https://$PUBLIC_HOST:$TS_PORTAL_PORT/register?invite=$TOKEN"
