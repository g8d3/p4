#!/usr/bin/env python3
"""e058 bin/volume.py — free spot-volume cache for the paper size filter.

Source: Binance public 24h ticker (keyless, $0, T1-auto).
Writes data/volume.json {ts, source, vols: {COIN: quoteVolume_usd}} for
coins seen in paper_calls + recent funding symbols, and appends one line
to data/volume_probe.jsonl. The card joins this into the paper grade as
sized (>= $1M 24h quote volume) vs thin-vol — thin steady pays are
suspected mirages.
Usage: python3 bin/volume.py [--coins A,B,C]
"""
import json
import os
import sqlite3
import sys
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'data.db')
OUT = os.path.join(BASE, 'data', 'volume.json')
LOG = os.path.join(BASE, 'data', 'volume_probe.jsonl')
URL = 'https://api.binance.com/api/v3/ticker/24hr'
FLOOR = 1_000_000  # sized vs thin-vol cutoff, USD quote volume


def coins_of_interest(extra):
    coins = set(extra or [])
    try:
        c = sqlite3.connect(DB)
        for (coin,) in c.execute('SELECT DISTINCT coin FROM paper_calls'):
            coins.add(str(coin).upper())
        for (coin,) in c.execute(
                "SELECT DISTINCT coin FROM funding WHERE ts >= "
                "(SELECT MAX(ts) FROM funding)"):
            coins.add(str(coin).upper())
        c.close()
    except Exception:
        pass
    return sorted(coins)


def main():
    extra = []
    if '--coins' in sys.argv:
        try:
            extra = sys.argv[sys.argv.index('--coins') + 1].split(',')
        except Exception:
            pass
    want = coins_of_interest([e.strip().upper() for e in extra if e.strip()])
    req = urllib.request.Request(URL, headers={'User-Agent': 'e058-volume/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        tickers = json.load(r)
    by_sym = {t.get('symbol', ''): t for t in tickers}
    vols, missing = {}, []
    for coin in want:
        for suffix in ('USDT', 'USDC', 'FDUSD'):
            t = by_sym.get(coin + suffix)
            if t:
                try:
                    vols[coin] = float(t.get('quoteVolume') or 0)
                except Exception:
                    missing.append(coin)
                break
        else:
            missing.append(coin)
    import datetime
    payload = {'ts': datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ'), 'source': 'binance-public-24hr-ticker',
        'cost': 0, 'floor_usd': FLOOR, 'vols': vols, 'missing': missing}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(payload, open(OUT, 'w'), indent=1)
    with open(LOG, 'a') as f:
        f.write(json.dumps({'ts': payload['ts'], 'n': len(vols),
                            'missing': len(missing)}) + '\n')
    sized = sum(1 for v in vols.values() if v >= FLOOR)
    print(f"volume ok: {len(vols)} coins, {sized} sized, "
          f"{len(missing)} missing -> {OUT}")


if __name__ == '__main__':
    main()
