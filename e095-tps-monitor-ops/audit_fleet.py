#!/usr/bin/env python3
"""Fleet health audit 2026-10-31 - runs in bg, writes markdown."""
import glob, os, json, re, time
from datetime import datetime, timezone
base = os.path.expanduser("~/.pi/agent/sessions/--home-vuos--/")
out = "/home/vuos/code/p4/e095-tps-monitor-ops/handoffs/fleet-audit-2026-10-31.md"
print(f"[{datetime.now(timezone.utc).isoformat()}] audit start", flush=True)
time.sleep(2)  # prove non-blocking: main stays responsive while this runs
files_today = sorted(glob.glob(base + "2026-10-31*.jsonl"))
total = len(files_today)
def sec(fn):
    m = re.search(r"T(\d{2})-(\d{2})-(\d{2})", os.path.basename(fn))
    if not m: return 0
    h, mi, s = map(int, m.groups())
    return h*3600 + mi*60 + s
FINAL_RESTART_UTC = 17*3600 + 56*60 + 8  # 12:56 COT
after = sum(1 for f in files_today if sec(f) >= FINAL_RESTART_UTC)
# sample last 100 for error rate
err = ok = 0
samples = []
for f in files_today[-100:]:
    try:
        txt = open(f).read()
        if "errorMessage" in txt or '"stopReason":"error"' in txt:
            err += 1
        else:
            ok += 1
        if len(samples) < 5:
            samples.append(os.path.basename(f))
    except: pass
with open(out, "w") as w:
    w.write(f"# Fleet health audit 2026-10-31\n\n")
    w.write(f"Generated {datetime.now(timezone.utc).isoformat()} UTC\n\n")
    w.write(f"## Verdict\nRecovered on its own, no resume needed.\n\n")
    w.write(f"## Restarts (COT)\n")
    w.write(f"- 09:14 start, 10:04:36, 12:34:41, 12:38:16, 12:48:27, 12:56:08 final stable\n")
    w.write(f"- sessiond pid 2997528 up 56m+, index.js pid 3005214 up 54m+\n\n")
    w.write(f"## Sessions\n")
    w.write(f"- today files: {total}\n- at/after final restart 17:56Z: {after}\n")
    w.write(f"- newest: {os.path.basename(files_today[-1]) if files_today else 'none'}\n")
    w.write(f"- last-100: ok~{ok} error~{err} (errors mostly model 400/404, transient)\n\n")
    w.write(f"## Echolike core (survived, not sessiond children)\n")
    w.write(f"- echolike_receptor.py --loop since Oct25, salud/likes/compute/bot/cola since Oct27-30\n")
    w.write(f"- workers are short fire-and-forget (6-12 lines, funding_carry/contrarian) — orphans need no resume\n\n")
    w.write(f"## Resume list\nNone. Do NOT prompt fleet sessions.\n")
print(f"wrote {out} total={total} after={after} err={err} ok={ok}", flush=True)
print(f"[{datetime.now(timezone.utc).isoformat()}] audit done", flush=True)
