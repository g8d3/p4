#!/usr/bin/env bash
# Pull authoritative usage from OpenCode Console (service key, no user tokens).
# Raw CSV -> log/ (ignored, contains emails). Aggregates -> ledger/usage-summary.json.
# Usage: OPENCODE_SERVICE_API_KEY=... bash bin/usage-pull.sh
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p log ledger
curl -s --fail-with-body --max-time 90 --get "https://opencode.ai/console/api/v1/usage/export" \
  --header "Authorization: Bearer ${OPENCODE_SERVICE_API_KEY:?set OPENCODE_SERVICE_API_KEY}" \
  --header "Accept: text/csv" \
  --data-urlencode "scope=organization" --data-urlencode "range=30d" \
  --output "log/usage-30d.csv" || { echo "pull FAILED"; exit 1; }
python3 - <<'EOF'
import csv, json, datetime
from collections import defaultdict
rows = list(csv.DictReader(open('log/usage-30d.csv')))
month = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m')
mtd = [r for r in rows if r['created_at'][:7] == month]
usd = sum(int(r['cost_micro_cents'] or 0) for r in mtd) / 100_000_000
by_model = defaultdict(lambda: [0, 0])
by_src = defaultdict(int)
for r in mtd:
    k = (r['provider'] or '?') + '/' + (r['model'] or r['service'] or '?')
    by_model[k][0] += int(r['input_tokens'] or 0)
    by_model[k][1] += int(r['output_tokens'] or 0)
    by_src[r['billing_source'] or '?'] += 1
daily = defaultdict(int)
for r in mtd:
    daily[r['created_at'][:10]] += int(r['input_tokens'] or 0) + int(r['output_tokens'] or 0)
top = sorted(by_model.items(), key=lambda x: -(x[1][0] + x[1][1]))[:6]
json.dump({"month": month, "records_mtd": len(mtd),
  "tokens_in": sum(v[0] for v in by_model.values()),
  "tokens_out": sum(v[1] for v in by_model.values()),
  "charged_usd": round(usd, 4),
  "by_source_rows": dict(by_src),
  "top_models": [{ "m": k, "in": v[0], "out": v[1] } for k, v in top],
  "active_days": len(daily),
  "pulled_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
  open('ledger/usage-summary.json', 'w'), indent=1)
print("summary:", open('ledger/usage-summary.json').read()[:400])
EOF
