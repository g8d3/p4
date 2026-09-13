#!/usr/bin/env python3
"""quota.py — OpenCode Go plan quota probe (T0 free, one HTTPS call).

No public usage API exists (upstream issue: web console only), so this
reuses the owner's web session cookie and parses the usage meters
embedded in the workspace page (same technique as hrbrmstr's
opencode-go-usage). Google-login flow never involved — cookie only.

Setup (once, owner):
  1. Log into opencode.ai in a browser, copy the `auth` cookie value.
  2. printf '%s' '<value>' > ~/.config/e062/opencode_cookie
     chmod 600 ~/.config/e062/opencode_cookie

Usage:
  quota.py            # print JSON meters (needs cookie)
  quota.py --beat     # update quota.json + beat ops on state change
                      # (warn at >=75% rolling, recovery ok, auth-fail blocked)

quota.json (this dir, git-ignored) feeds the :8322 board quota badge.
"""
import json
import os
import re
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.expanduser('~/.config/e062/opencode_cookie')
OUT = os.path.join(BASE, 'quota.json')
WORKSPACE = os.environ.get('OPENCODE_WORKSPACE',
                           'wrk_01KK38YMZBBZB3AHED1ZVHMM7E')
OPS = os.path.join(BASE, 'bin', 'ops.py')
WARN_PCT = 75


def fetch():
    try:
        with open(COOKIE_FILE) as f:
            cookie = f.read().strip()
    except Exception:
        return {'ok': False, 'error': 'no cookie',
                'hint': 'paste auth cookie to ~/.config/e062/opencode_cookie'}
    if not cookie:
        return {'ok': False, 'error': 'empty cookie'}
    url = f'https://opencode.ai/workspace/{WORKSPACE}/go'
    req = urllib.request.Request(
        url, headers={'Cookie': f'auth={cookie}',
                      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            final, html = r.geturl(), r.read().decode('utf-8', 'replace')
    except Exception as e:
        return {'ok': False, 'error': f'fetch failed: {e}'}
    if re.search(r'openauth|sign-?in|log-?in', final, re.I) and 'workspace' not in final:
        return {'ok': False, 'error': 'session expired (redirected to login)',
                'hint': 're-paste auth cookie'}
    return parse(html)


def parse(html):
    meters = {}
    for name in ('rolling', 'weekly', 'monthly'):
        m = re.search(rf'"{name}"\s*:\s*\{{\s*"percent"\s*:\s*(\d+)'
                      rf'[^}}]*?"reset_in_sec"\s*:\s*(\d+)', html)
        if m:
            meters[name] = {'percent': int(m.group(1)),
                            'reset_in_sec': int(m.group(2)), 'status': 'ok'}
    if len(meters) == 3:
        meters.update({'plan': 'Go',
                       'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                                   time.gmtime()),
                       'ok': True})
        return meters
    open(os.path.join(BASE, 'quota_debug.html'), 'w').write(html[:200000])
    return {'ok': False, 'error': 'meters not found in page',
            'hint': 'page shape changed; see quota_debug.html'}


def beat(msg_kind, summary):
    import subprocess
    try:
        subprocess.run([sys.executable, OPS, 'beat', 'runner', msg_kind,
                        summary], capture_output=True, timeout=20)
    except Exception:
        pass


def main(args):
    data = fetch()
    if '--beat' in args:
        prev = {}
        try:
            prev = json.load(open(OUT))
        except Exception:
            pass
        json.dump(data, open(OUT, 'w'))
        if not data.get('ok'):
            if prev.get('ok', True):
                beat('blocked',
                     'Quota probe blind — re-paste the opencode cookie | '
                     f"tech: quota.py: {data.get('error')}")
            print(json.dumps(data))
            return 1
        rp = data['rolling']['percent']
        pp = (prev.get('rolling') or {}).get('percent', 0)
        if rp >= WARN_PCT and pp < WARN_PCT:
            beat('step',
                 f'Quota {rp}% into the 5h window — heavy legs wait | '
                 f'tech: quota.py rolling={rp}% weekly={data["weekly"]["percent"]}% '
                 f'monthly={data["monthly"]["percent"]}%')
        elif rp < WARN_PCT and pp >= WARN_PCT:
            beat('ok',
                 'Quota window recovered, legs run free | '
                 f'tech: quota.py rolling back to {rp}%')
        print(json.dumps(data))
        return 0
    print(json.dumps(data, indent=1))
    return 0 if data.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
