#!/bin/bash
# e062 rung-3 e2e: verifies fleet board root + /api/board JSON shape. Exit nonzero on any failure.
# Usage: tests/e2e.sh [base_url]   (default http://100.102.52.59:8322)
BASE="${1:-http://100.102.52.59:8322}"
fail() { echo "E2E FAIL: $1"; exit 1; }

code=$(curl -s -m 10 -o /tmp/e62_root.html -w "%{http_code}" "$BASE/") || fail "root unreachable"
[ "$code" = "200" ] || fail "root http=$code"
grep -q "fleet board" /tmp/e62_root.html || fail "board missing title"

curl -s -m 15 "$BASE/api/board" -o /tmp/e62_board.json || fail "board API unreachable"
python3 - <<'EOF' || fail "board shape bad"
import json
d = json.load(open("/tmp/e62_board.json"))
tracks = d.get("tracks")
assert isinstance(tracks, list) and len(tracks) >= 5, "tracks < 5"
names = {t["track"] for t in tracks}
assert {"e058", "e059", "e060", "e061", "e062"} <= names, f"missing tracks: {names}"
for t in tracks:
    assert "rung" in t and "beat" in t, f"track {t.get('track')} missing rung/beat"
rw = d.get("runway", {})
for k in ("spent", "earned", "left"):
    assert k in rw, f"runway missing {k}"
print(f"board ok: {len(tracks)} tracks, runway left=${rw['left']:.2f}")
EOF
echo "E2E PASS ($BASE)"
