#!/usr/bin/env bash
# e066 launch-watch: one-command Arc-launch probe (free DefiLlama, no key).
# Numeric-source rule (run #103): launch counts ONLY on exact-name chain
# with tvl>0 — name-substring matches (Archway/Starcoin) and chainid
# squats (ARC Mainnet 1243, no explorer/TVL) never count.
# Usage: bin/launch_watch.sh  -> prints LAUNCH <name> tvl=<n> | PRE-LAUNCH <chains> chains, squats ignored
set -u
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
timeout 25 curl -s "https://api.llama.fi/chains" -o "$TMP" || { echo "PROBE-FAIL fetch error"; exit 1; }
timeout 30 python3 - "$TMP" <<'EOF' || { echo "PROBE-FAIL parse error"; exit 1; }
import json, sys
d = json.load(open(sys.argv[1]))
exact = [c for c in d if str(c.get("name", "")).lower() == "arc" and (c.get("tvl") or 0) > 0]
squats = [c.get("name") for c in d if "arc" in str(c.get("name", "")).lower() and c not in exact][:5]
if exact:
    print("LAUNCH %s tvl=%s" % (exact[0]["name"], exact[0]["tvl"]))
else:
    print("PRE-LAUNCH %d chains, squats ignored=%s" % (len(d), squats))
EOF
