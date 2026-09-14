#!/usr/bin/env python3
"""e062 tax-report export scaffold (TAX doctrine 2026-09-14).

Reads the money-action ledger and emits report-ready JSON/CSV with columns:
  ts, iso8601, track, kind, amount_usd, tx_hash, notes

- `tx_hash` column holds the on-chain transaction hash for on-chain actions
  (empty for off-chain/paper spends). If the column is missing it is added
  (ALTER TABLE migration); if empty but the note embeds a 0x-hash, the
  export surfaces it as a fallback so nothing is lost.
- Filters: --track e058 --year 2026 --kind earn|spend
- Usage:
    bin/tax_export.py [--format json|csv|both] [--out DIR] [--track T] [--year Y] [--kind K]
    bin/tax_export.py --migrate-only   # just ensure tx_hash column exists
"""
import argparse
import csv
import datetime
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get('E062_DB', os.path.join(BASE, '..', 'ops.db'))

HASH_RE = re.compile(r'0x[0-9a-fA-F]{16,}')

COLUMNS = ['ts', 'iso8601', 'track', 'kind', 'amount_usd', 'tx_hash', 'notes']


def connect():
    return sqlite3.connect(DB)


def ensure_tx_hash_column(c):
    cols = [r[1] for r in c.execute('PRAGMA table_info(ledger)').fetchall()]
    if 'tx_hash' not in cols:
        c.execute("ALTER TABLE ledger ADD COLUMN tx_hash TEXT DEFAULT ''")
        c.commit()
        print('migrated: ledger.tx_hash column added')
    return 'tx_hash' in [r[1] for r in c.execute('PRAGMA table_info(ledger)').fetchall()]


def fetch(track=None, year=None, kind=None):
    c = connect()
    cols = [r[1] for r in c.execute('PRAGMA table_info(ledger)').fetchall()]
    has_hash = 'tx_hash' in cols
    sel = 'ts, track, kind, usd, note' + (', tx_hash' if has_hash else '')
    rows = c.execute(f'SELECT {sel} FROM ledger ORDER BY ts').fetchall()
    c.close()
    out = []
    for r in rows:
        ts, tr, kd, usd, note = r[0], r[1], r[2], r[3], r[4] or ''
        txh = (r[5] or '') if has_hash and len(r) > 5 else ''
        if not txh:
            m = HASH_RE.search(note)
            if m:
                txh = m.group(0)
        if track and tr != track:
            continue
        if kind and kd != kind:
            continue
        dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
        if year and dt.year != year:
            continue
        out.append({
            'ts': ts,
            'iso8601': dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'track': tr,
            'kind': kd,
            'amount_usd': float(usd),
            'tx_hash': txh,
            'notes': note,
        })
    return out


def summary(rows):
    spent = sum(r['amount_usd'] for r in rows if r['kind'] == 'spend')
    earned = sum(r['amount_usd'] for r in rows if r['kind'] == 'earn')
    onchain = sum(1 for r in rows if r['tx_hash'])
    return {'n': len(rows), 'spent_usd': round(spent, 2),
            'earned_usd': round(earned, 2), 'net_usd': round(earned - spent, 2),
            'onchain_actions': onchain}


def main():
    ap = argparse.ArgumentParser(description='Export ledger to tax-report JSON/CSV')
    ap.add_argument('--format', default='both', choices=['json', 'csv', 'both'])
    ap.add_argument('--out', default=os.path.join(BASE, '..', 'runs'),
                    help='output directory (default: runs/)')
    ap.add_argument('--track', default=None)
    ap.add_argument('--year', type=int, default=None)
    ap.add_argument('--kind', default=None, choices=['spend', 'earn'])
    ap.add_argument('--migrate-only', action='store_true')
    ap.add_argument('--stdout', action='store_true', help='print JSON to stdout instead of files')
    a = ap.parse_args()

    c = connect()
    ensure_tx_hash_column(c)
    c.close()
    if a.migrate_only:
        return 0

    rows = fetch(track=a.track, year=a.year, kind=a.kind)
    rep = {'exported_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           'db': os.path.basename(DB), 'filters': {'track': a.track, 'year': a.year, 'kind': a.kind},
           'columns': COLUMNS, 'summary': summary(rows), 'rows': rows}

    if a.stdout or not a.out:
        print(json.dumps(rep, indent=2))
        return 0

    os.makedirs(a.out, exist_ok=True)
    tag = 'tax_export'
    if a.track:
        tag += f'_{a.track}'
    if a.year:
        tag += f'_{a.year}'
    made = []
    if a.format in ('json', 'both'):
        jp = os.path.join(a.out, tag + '.json')
        with open(jp, 'w') as f:
            json.dump(rep, f, indent=2)
        made.append(jp)
    if a.format in ('csv', 'both'):
        cp = os.path.join(a.out, tag + '.csv')
        with open(cp, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        made.append(cp)
    print(f"tax export: {rep['summary']['n']} rows, "
          f"spent ${rep['summary']['spent_usd']:.2f} earned ${rep['summary']['earned_usd']:.2f} "
          f"net ${rep['summary']['net_usd']:.2f}, on-chain {rep['summary']['onchain_actions']}")
    for p in made:
        print(f'wrote {p}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
