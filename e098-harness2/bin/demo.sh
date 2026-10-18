#!/bin/bash
# Re-run the no-credential local demo, then re-render the site.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
NEEDS="$HERE/needs.json"
UP="$(python3 -c "import json;print(json.load(open('$NEEDS'))['upstream_dir'])")"
OUT="$(python3 -c "import json;print(json.load(open('$NEEDS'))['demo_output'])")"
K="${1:-2}"
"$UP/.venv/bin/harness2-demo" --output "$OUT" --k "$K"
python3 "$HERE/bin/render.py"
