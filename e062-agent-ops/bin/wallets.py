#!/usr/bin/env python3
"""wallets.py — real funds, not fiction (T0 free, public RPCs, no keys).

Reads native (+USDC on Arbitrum) balances for registered wallets and
USD prices, writes wallets_cache.json for the board. Addresses are
public; private keys never touch this system.

  wallets.py --json      # probe now, print JSON
  wallets.py --update    # probe + write cache (cron)

wallets.json (this dir, git-ignored, owner-maintained):
  [{"label": "main", "chain": "arbitrum",
    "address": "0x..."}]
"""
import json
import os
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLETS = os.path.join(BASE, 'wallets.json')
CACHE = os.path.join(BASE, 'wallets_cache.json')
PRICE_CACHE = os.path.join(BASE, 'wallets_prices.json')

RPC = {
    'arbitrum': ['https://arb1.arbitrum.io/rpc',
                 'https://arbitrum-one.publicnode.com',
                 'https://arbitrum.drpc.org'],
    'ethereum': ['https://ethereum-rpc.publicnode.com'],
}
UA = {'Content-Type': 'application/json',
      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
USDC = {'arbitrum': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831'}.get
USDC_ARB = '0xaf88d065e77c8cC2239327C5EDb3A432268e5831'


def rpc(chain, method, params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1,
                       'method': method, 'params': params}).encode()
    last = None
    for url in RPC[chain]:
        try:
            req = urllib.request.Request(url, data=body, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r).get('result')
        except Exception as e:
            last = e
    raise RuntimeError(str(last)[:120])


def prices():
    try:
        pc = json.load(open(PRICE_CACHE))
        if time.time() - pc.get('ts', 0) < 3600:
            return pc['prices']
    except Exception:
        pass
    url = ('https://api.coingecko.com/api/v3/simple/price'
           '?ids=ethereum,usd-coin&vs_currencies=usd')
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            p = json.load(r)
        out = {'eth': float(p['ethereum']['usd']),
               'usdc': float(p['usd-coin']['usd'])}
    except Exception:
        out = {'eth': 0.0, 'usdc': 1.0}
    json.dump({'ts': time.time(), 'prices': out}, open(PRICE_CACHE, 'w'))
    return out


def balance(w, px):
    chain, addr = w['chain'], w['address']
    native = 0.0
    try:
        native = int(rpc(chain, 'eth_getBalance', [addr, 'latest']), 16) / 1e18
    except Exception:
        pass
    usdc = 0.0
    if chain == 'arbitrum':
        try:
            data = '0x70a08231' + '0' * 24 + addr[2:].lower()
            r = rpc(chain, 'eth_call',
                    [{'to': USDC_ARB, 'data': data}, 'latest'])
            usdc = int(r, 16) / 1e6
        except Exception:
            pass
    usd = round(native * px['eth'] + usdc * px['usdc'], 2)
    return {'label': w.get('label', addr[:8]), 'chain': chain,
            'address': addr, 'native': round(native, 6),
            'usdc': round(usdc, 2), 'usd': usd}


def probe():
    try:
        wallets = json.load(open(WALLETS))
    except Exception:
        return {'ok': False, 'error': 'no wallets.json',
                'hint': 'add [{"label","chain","address"}] to wallets.json'}
    if not wallets:
        return {'ok': False, 'error': 'no wallets registered'}
    px = prices()
    rows = [balance(w, px) for w in wallets
            if w.get('chain') in RPC and w.get('address', '').startswith('0x')]
    total = round(sum(r['usd'] for r in rows), 2)
    return {'ok': True, 'total_usd': total, 'n': len(rows),
            'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'wallets': rows}


def main(args):
    d = probe()
    if '--update' in args and d.get('ok'):
        json.dump(d, open(CACHE, 'w'))
    print(json.dumps(d, indent=1))
    return 0 if d.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
