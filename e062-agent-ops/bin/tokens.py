#!/usr/bin/env python3
"""tokens.py — session token probe (T0 free, local files only).

Usage:
  tokens.py <session.jsonl> [--json]   # one session
  tokens.py --leg <run_start_ts> [--json]  # newest leg session in pi store

Reports honest numbers from pi's per-message usage records:
start_tokens (the "hola cost"), end_tokens, growth, in/out split,
cache share, cost. No estimates.
"""
import glob
import json
import os
import sys


def usages(path):
    """All usage dicts in file order (one per assistant turn)."""
    out = []
    with open(path) as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            if not isinstance(o, dict):
                continue
            stack = [o]
            while stack:
                x = stack.pop()
                if isinstance(x, dict):
                    u = x.get('usage')
                    if isinstance(u, dict) and 'totalTokens' in u:
                        out.append(u)
                        continue  # don't descend into a counted usage
                    stack.extend(x.values())
                elif isinstance(x, list):
                    stack.extend(x)
    return out


def summarize(path):
    us = usages(path)
    if not us:
        return {'file': path, 'turns': 0}
    start = int(us[0].get('totalTokens') or 0)
    end = max(int(u.get('totalTokens') or 0) for u in us)
    s_in = sum(int(u.get('input') or 0) for u in us)
    s_out = sum(int(u.get('output') or 0) for u in us)
    s_cache = sum(int(u.get('cacheRead') or 0) for u in us)
    cost = sum(float((u.get('cost') or {}).get('total') or 0) for u in us)
    return {
        'file': os.path.basename(path),
        'turns': len(us),
        'start_tokens': start,
        'end_tokens': end,
        'growth': end - start,
        'sum_in': s_in,
        'sum_out': s_out,
        'cache_read': s_cache,
        'cost_usd': round(cost, 6),
        'first_share': round(start / end, 3) if end else 0,
    }


def leg_file(run_start_ts, margin=60):
    root = os.path.expanduser('~/.pi/agent/sessions')
    best, best_mtime = None, 0
    for p in glob.glob(os.path.join(root, '**', '*.jsonl'), recursive=True):
        try:
            mt = int(os.path.getmtime(p))
        except Exception:
            continue
        if mt >= int(run_start_ts) - margin and mt > best_mtime:
            best, best_mtime = p, mt
    return best


def main(args):
    as_json = '--json' in args
    args = [a for a in args if a != '--json']
    if len(args) >= 2 and args[0] == '--leg':
        p = leg_file(args[1])
        if not p:
            print(json.dumps({'error': 'no session file found'}))
            return 1
    elif len(args) >= 1:
        p = args[0]
    else:
        print(__doc__)
        return 2
    s = summarize(p)
    if as_json:
        print(json.dumps(s))
    else:
        if not s.get('turns'):
            print(f"{s['file']}: no usage records")
            return 0
        print(f"{s['file']}: {s['turns']} turns, "
              f"{s['start_tokens']} -> {s['end_tokens']} "
              f"(+{s['growth']}, hola-share {s['first_share']:.0%})")
        print(f"  in {s['sum_in']} / out {s['sum_out']} / "
              f"cached {s['cache_read']} / cost ${s['cost_usd']:.4f}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
