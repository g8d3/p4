#!/usr/bin/env python3
"""e058 backtest: do persistent-spread signals hold up? (T0, saved data only)

Same survivor rule as /api/persistence (spread >= threshold in ALL of the
last_n snapshots, >= min_legs venues, DEX-only): for every historical
snapshot with 24h of follow-up data, record survivors, then check each
survivor coin at the first snapshot >= 24h later. Hit = spread still >=
threshold. Writes track-root backtest.json (committed, served by /api/backtest).

Usage: bin/backtest.py [--threshold 20] [--last-n 4] [--min-legs 2] [--force]
Skips recompute when backtest.json is < 6h old unless --force.
"""
import json, os, sqlite3, sys, time, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'data.db')
OUT = os.path.join(BASE, 'backtest.json')
DEX29 = ['zo', 'aster', 'bluefin', 'bullet', 'decibel', 'edgex', 'entropyio',
         'extended', 'hibachi', 'hyperliquid', 'lighter', 'pacifica', 'paradex',
         'variational', 'vest', 'txflow', 'nostra', 'avalon', 'elixir', 'drift',
         'jupiter', 'ostium', 'synthetix', 'gmx', 'apex', 'dydx', 'grvt',
         'wine', 'orderly']

def parse_ts(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))

def main():
    thr, last_n, min_legs, force = 20.0, 4, 2, False
    a = sys.argv[1:]
    while a:
        k = a.pop(0)
        if k == '--threshold': thr = float(a.pop(0))
        elif k == '--last-n': last_n = int(a.pop(0))
        elif k == '--min-legs': min_legs = int(a.pop(0))
        elif k == '--force': force = True
    if not force and os.path.exists(OUT):
        age_h = (time.time() - os.path.getmtime(OUT)) / 3600
        if age_h < 6:
            d = json.load(open(OUT))
            print(f"backtest fresh ({age_h:.1f}h): {d.get('summary')}")
            return
    t0 = time.time()
    c = sqlite3.connect(DB)
    snaps = [r[0] for r in c.execute('SELECT DISTINCT ts FROM funding ORDER BY ts')]
    tss = [parse_ts(s) for s in snaps]
    q = ('SELECT ts, coin, venue, bps8 FROM funding WHERE venue IN (%s)'
         % ','.join('?' * len(DEX29)))
    per = {}
    for ts, coin, venue, bps in c.execute(q, DEX29):
        try: b = float(bps)
        except (TypeError, ValueError): continue
        per.setdefault((ts, coin), []).append((venue, b))
    c.close()
    # per (ts, coin) -> spread (None if < min_legs)
    spread = {}
    apy_of = {}
    for (ts, coin), legs in per.items():
        if len(legs) < min_legs:
            spread[(ts, coin)] = None
            continue
        lo = min(b for _, b in legs); hi = max(b for _, b in legs)
        s = hi - lo
        spread[(ts, coin)] = round(s, 2)
        apy_of[(ts, coin)] = round(s / 100 * 3 * 365, 1)
    coins = {coin for (_, coin) in spread}
    sig, hit, decays = 0, 0, []
    first_i, last_eval = None, None
    for i in range(last_n - 1, len(snaps)):
        # need a snapshot >= 24h after snaps[i]
        cutoff = tss[i] + datetime.timedelta(hours=24)
        j = next((k for k in range(i + 1, len(snaps)) if tss[k] >= cutoff), None)
        if j is None: break
        if first_i is None: first_i = snaps[i]
        last_eval = snaps[i]
        win = snaps[i - last_n + 1:i + 1]
        for coin in coins:
            if any((spread.get((w, coin)) or -1) < thr for w in win):
                continue
            sig += 1
            s_out = spread.get((snaps[j], coin))
            if s_out is not None and s_out >= thr:
                hit += 1
                a0 = apy_of.get((snaps[i], coin)) or 0
                a1 = apy_of.get((snaps[j], coin)) or 0
                if a0 > 0: decays.append(round(a1 / a0, 3))
    decays.sort()
    rate = round(100 * hit / sig, 1) if sig else 0.0
    med_decay = decays[len(decays) // 2] if decays else None
    d = {'ok': True, 'track': 'e058', 'threshold_bps': thr, 'last_n': last_n,
         'min_legs': min_legs, 'lookahead_h': 24,
         'window_first': first_i, 'window_last': last_eval,
         'n_signals': sig, 'n_hit': hit, 'hit_rate_pct': rate,
         'median_apy_decay': med_decay,
         'computed_ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
         'elapsed_s': round(time.time() - t0, 1)}
    d['summary'] = (f"{rate}% of steady calls still paying 24h later "
                    f"({hit}/{sig}, median APY kept {med_decay}x)" if sig
                    else "no persistent signals in window")
    json.dump(d, open(OUT, 'w'), indent=1)
    print(f"backtest: {d['summary']} [{d['elapsed_s']}s] -> {OUT}")

if __name__ == '__main__':
    main()
