#!/usr/bin/env python3
"""Enrich Loris funding snapshot with per-leg venue liquidity (OI + depth).
Usage: enrich.py <funding.json> [TOPN]
Public APIs only, no keys. Missing data -> n/a (itself a signal: unexecutable).
"""
import json, sys, urllib.request

UA = {'User-Agent': 'Mozilla/5.0'}
DEX29 = ['zo','aster','bluefin','bullet','decibel','edgex','entropyio','extended',
 'grvt','hibachi','hotstuff','hyperliquid','kinetiq','lighter','nado','ondo',
 'pacifica','paradex','paragon','phoenix','qfex','reya','risex','tradexyz',
 'txflow','variational','vest','woofipro']
EXEC = ['hyperliquid', 'aster', 'paradex', 'extended', 'lighter']  # fundable rails

def get(url, data=None, timeout=20):
    req = urllib.request.Request(url, data=data,
        headers={**UA, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def depth_usd(levels, px_idx=0, sz_idx=1, band=0.01):
    """levels: list of [price, size]. Mid from best bid/ask assumed pre-split."""
    return None

def book_depth(bids, asks, band=0.01):
    try:
        best_bid = float(bids[0][0]); best_ask = float(asks[0][0])
    except Exception:
        return None
    mid = (best_bid + best_ask) / 2
    tot = 0.0
    for px, sz in bids:
        px = float(px); sz = float(sz)
        if (mid - px) / mid <= band: tot += px * sz
        else: break
    for px, sz in asks:
        px = float(px); sz = float(sz)
        if (px - mid) / mid <= band: tot += px * sz
        else: break
    return tot

# ---- venue caches ----
HL = {}   # coin -> (oi_usd, mark)
def hl_meta():
    if HL: return HL
    d = get('https://api.hyperliquid.xyz/info',
            data=json.dumps({'type': 'metaAndAssetCtxs'}).encode())
    for u, c in zip(d[0]['universe'], d[1]):
        try: HL[u['name']] = (float(c.get('openInterest', 0)) * float(c.get('markPx', 0)),
                              float(c.get('markPx', 0)))
        except Exception: pass
    return HL

def _pairs(levels):
    out=[]
    for x in levels:
        if isinstance(x, dict): out.append((x.get('px'), x.get('sz')))
        else: out.append((x[0], x[1]))
    return out

def hl_book(coin):
    try:
        d = get('https://api.hyperliquid.xyz/info',
                data=json.dumps({'type': 'l2Book', 'coin': coin}).encode())
        return book_depth(_pairs(d['levels'][0]), _pairs(d['levels'][1]))
    except Exception: return None

def aster_book(sym):
    try:
        d = get(f'https://fapi.asterdex.com/fapi/v1/depth?symbol={sym}USDT&limit=100')
        return book_depth(d['bids'], d['asks'])
    except Exception: return None

def aster_oi(sym):
    try:
        o = get(f'https://fapi.asterdex.com/fapi/v1/openInterest?symbol={sym}USDT')
        m = get(f'https://fapi.asterdex.com/fapi/v1/premiumIndex?symbol={sym}USDT')
        return float(o['openInterest']) * float(m['markPrice'])
    except Exception: return None

def paradex_book(sym):
    try:
        d = get(f'https://api.prod.paradex.trade/v1/orderbook/{sym}-USD-PERP?depth=50')
        return book_depth(d['bids'], d['asks'])
    except Exception: return None

def ext_book(sym):
    try:
        d = get(f'https://api.starknet.extended.exchange/api/v1/info/markets/{sym}-USD/orderbook')
        b, a = d['data']['bid'], d['data']['ask']
        return book_depth([(x['price'], x['qty']) for x in b],
                          [(x['price'], x['qty']) for x in a])
    except Exception: return None

def ext_oi(sym):
    try:
        d = get(f'https://api.starknet.extended.exchange/api/v1/info/{sym}-USD/open-interests?interval=1h')
        dd = d['data']
        lst = dd if isinstance(dd, list) else dd.get('data', dd.get('openInterests', []))
        tot = 0.0
        for e in (lst or []):
            tot += float(e.get('openInterest', e.get('size', 0) or 0)) * float(e.get('markPrice', e.get('price', 0) or 0))
        return tot or None
    except Exception: return None

LIGHTER = None
def lighter_meta():
    global LIGHTER
    if LIGHTER is None:
        try:
            d = get('https://mainnet.zklighter.elliot.ai/api/v1/orderBookDetails')
            LIGHTER = {x['symbol']: x for x in d['order_book_details']}
        except Exception: LIGHTER = {}
    return LIGHTER

def fmt(x):
    if x is None: return 'n/a'
    if x >= 1e6: return f'${x/1e6:.1f}M'
    if x >= 1e3: return f'${x/1e3:.0f}k'
    return f'${x:.0f}'

def leg_liq(ex, sym):
    """Return (oi_usd, depth1pct_usd)."""
    try:
        if ex == 'hyperliquid':
            m = hl_meta(); oi, _ = m.get(sym, (None, None)); return oi, hl_book(sym)
        if ex == 'aster': return aster_oi(sym), aster_book(sym)
        if ex == 'paradex': return None, paradex_book(sym)
        if ex == 'extended': return ext_oi(sym), ext_book(sym)
        if ex == 'lighter':
            m = lighter_meta().get(sym)
            if not m: return None, None
            try: oi = float(m['open_interest']) * float(m['mark_price'])
            except Exception: oi = None
            return oi, None
    except Exception: pass
    return None, None

def main():
    f = json.load(open(sys.argv[1]))
    topn = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    fr = f['funding_rates']
    print('payload ts:', f.get('timestamp'))
    rows = []
    for sym in f['symbols']:
        legs = [(ex, fr[ex][sym]) for ex in DEX29 if ex in fr and sym in fr[ex]]
        if len(legs) < 2: continue
        lo = min(legs, key=lambda x: x[1]); hi = max(legs, key=lambda x: x[1])
        apy = (hi[1] - lo[1]) / 100 * 3 * 365
        rows.append((apy, sym, lo, hi))
    rows.sort(reverse=True)
    print(f"{'APY%':>8} {'SYM':8} {'long-leg':22} {'short-leg':22}")
    for apy, sym, lo, hi in rows[:topn]:
        lo_oi, lo_dp = leg_liq(lo[0], sym) if lo[0] in EXEC else (None, None)
        hi_oi, hi_dp = leg_liq(hi[0], sym) if hi[0] in EXEC else (None, None)
        ex_note = '' if (lo[0] in EXEC and hi[0] in EXEC) else '  [leg outside fundable set]'
        print(f'{apy:8.1f} {sym:8} {lo[0]}:{lo[1]:.2f} {hi[0]}:{hi[1]:.2f}{ex_note}')
        print(f'           OI   long {fmt(lo_oi):>8}  short {fmt(hi_oi):>8}')
        print(f'           ±1%  long {fmt(lo_dp):>8}  short {fmt(hi_dp):>8}')

main()
