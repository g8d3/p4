#!/usr/bin/env python3
"""e058 retention prune: cap SQLite + data/ growth ( fleet: wire to cron).

Deletes funding/symbols rows older than --days (default 14), drops
ingested data/loris_cap_* files older than --days, then VACUUMs.
Paper grading needs ~2 days, backtest window ~3 days — 14 is plenty safe.
Run: python3 bin/prune.py [--days 14] [--apply]  (dry-run by default)
"""
import datetime, glob, os, sqlite3, sys, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get('E058_DB', os.path.join(BASE, 'data.db'))
DAYS = 14
APPLY = '--apply' in sys.argv
for a in sys.argv[1:]:
    if a.startswith('--days='):
        try: DAYS = max(2, int(a.split('=', 1)[1]))
        except ValueError: pass

cutoff = (datetime.datetime.now(datetime.timezone.utc)
          - datetime.timedelta(days=DAYS)).strftime('%Y-%m-%dT%H:%M:%SZ')
print(f'cutoff ts < {cutoff}  ({"APPLY" if APPLY else "dry-run, pass --apply"})')

c = sqlite3.connect(DB)
for tbl in ('funding', 'symbols'):
    try:
        n = c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE ts < ?", (cutoff,)).fetchone()[0]
        print(f'{tbl}: {n} rows older than cutoff')
        if APPLY and n:
            c.execute(f"DELETE FROM {tbl} WHERE ts < ?", (cutoff,))
            print(f'{tbl}: deleted {n}')
    except Exception as e:
        print(f'{tbl}: skip ({e})')
if APPLY:
    c.commit()
    before = os.path.getsize(DB)
    c.execute('VACUUM')
    after = os.path.getsize(DB)
    print(f'VACUUM: {before/1e6:.0f}M -> {after/1e6:.0f}M')
c.close()

old = [p for p in glob.glob(os.path.join(BASE, 'data', 'loris_cap_*'))
       if os.path.getmtime(p) < time.time() - DAYS * 86400]
print(f'data/: {len(old)} ingested files older than {DAYS}d '
      f'({sum(os.path.getsize(p) for p in old)/1e6:.0f}M)')
if APPLY:
    for p in old:
        try: os.remove(p)
        except OSError: pass
    print('data/: old files removed (alert_state.json kept)')
