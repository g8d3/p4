#!/usr/bin/env bash
# Credit meter: no API needed. Reads per-session cost/tokens from the local
# opencode ledger (~/.local/share/opencode/opencode.db) and reports against
# the declared cap in ledger/BUDGET. Usage: bash bin/credits-meter.sh
set -uo pipefail
cd "$(dirname "$0")/.."
DB=/home/vuos/.local/share/opencode/opencode.db
CAP=$(grep -m1 '^cap_usd=' ledger/BUDGET 2>/dev/null | cut -d= -f2)
CAP="${CAP:-unlimited}"
python3 - "$DB" "$CAP" <<'EOF'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
cap = sys.argv[2]
q = lambda sql, a=(): db.execute(sql, a).fetchone()
d7 = q("select coalesce(sum(cost),0), coalesce(sum(tokens_input),0), coalesce(sum(tokens_output),0) from session where datetime(time_updated/1000,'unixepoch') >= datetime('now','-7 days')")
td = q("select coalesce(sum(cost),0) from session where date(datetime(time_updated/1000,'unixepoch')) = date('now')")
print(f"7d spend: ${d7[0]:.2f} | in: {d7[1]:,} out: {d7[2]:,}")
print(f"today:    ${td[0]:.2f}")
print("by model (7d):")
for m, c in db.execute("select model, sum(cost) from session where datetime(time_updated/1000,'unixepoch') >= datetime('now','-7 days') group by model order by sum(cost) desc limit 5"):
    print(f"  ${c:.2f}  {m[:60]}")
print(f"cap: {cap}", end="")
# pi session files carry per-call usage (no API anywhere; this is the meter)
import os, re, time
pi_in = pi_out = 0
pi_cost = 0.0
cutoff = time.time() - 7 * 86400
root = os.path.expanduser('~/.pi/agent/sessions')
pat = re.compile(r'"usage":\{"input":(\d+),"output":(\d+),[^}]*?"total":([0-9.e-]+)\}')
for dp, _, fns in os.walk(root):
    for fn in fns:
        p = os.path.join(dp, fn)
        try:
            if os.path.getmtime(p) < cutoff:
                continue
            raw = open(p, errors='ignore').read()
        except OSError:
            continue
        for a, b, c in pat.findall(raw):
            pi_in += int(a); pi_out += int(b)
            try: pi_cost += float(c)
            except ValueError: pass
print(f"\npi sessions (7d): ${pi_cost:.4f} | in: {pi_in:,} out: {pi_out:,}", end="")
print(f"\ncombined 7d measured: ${d7[0] + pi_cost:.4f}", end="")
# month-to-date vs plan: owner routinely uses <50%, so pace matters, not the cap
mtd = q("select coalesce(sum(cost),0) from session where strftime('%Y-%m', datetime(time_updated/1000,'unixepoch')) = strftime('%Y-%m','now')")[0]
import calendar
import datetime
now = datetime.datetime.now(datetime.timezone.utc)
days_in = calendar.monthrange(now.year, now.month)[1]
left = days_in - now.day + 1
print(f"\nMTD db-measured: ${mtd:.2f} | day {now.day}/{days_in} ({left} left)", end="")
if cap not in ("unlimited", ""):
    try:
        rem = float(cap) - d7[0]
        print(f" | remaining: ${rem:.2f}")
    except ValueError:
        print(" (unparseable)")
else:
    print(" (owner order: use all)")
EOF
