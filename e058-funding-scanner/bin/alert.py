#!/usr/bin/env python3
"""e058 Telegram alerts for persistent funding spreads.
Reads /api/persistence (or --db directly), sends top survivors via Bot API.
Secrets ONLY from env: E058_TG_TOKEN, E058_TG_CHAT. Never commit them.
State: data/alert_state.json (git-ignored) skips already-alerted windows.
Test (dry run, no Telegram call):  python3 bin/alert.py --dry-run"""
import json, os, sqlite3, sys, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BASE, 'data', 'alert_state.json')
TOP_N = 10

def get_rows(endpoint, db_path, threshold_bps, last_n):
    if endpoint:
        with urllib.request.urlopen(
                f'{endpoint}/api/persistence?threshold_bps={threshold_bps}&last_n={last_n}',
                timeout=30) as r:
            return json.load(r)
    sys.path.insert(0, BASE)
    import importlib.util
    spec = importlib.util.spec_from_file_location('e058app', os.path.join(BASE, 'app.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    os.environ['E058_DB'] = db_path
    m.DB = db_path
    return m.persistence(threshold_bps=threshold_bps, last_n=last_n)

def send(token, chat, text):
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data=urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode(),
        timeout=30)
    with urllib.request.urlopen(req) as r:
        return json.load(r).get('ok', False)

def send_ntfy(text, title='e058 funding'):
    import os
    topic = os.environ.get('NTFY_TOPIC')
    if not topic:
        sys.exit('missing NTFY_TOPIC env')
    server = os.environ.get('NTFY_SERVER', 'https://ntfy.sh').rstrip('/')
    req = urllib.request.Request(f'{server}/{topic}', data=text.encode(),
        headers={'Title': title, 'Priority': 'default', 'Tags': 'chart_with_upwards_trend'},
        method='POST', timeout=30)
    with urllib.request.urlopen(req) as r:
        return r.status in (200, 202)

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--endpoint', default=os.environ.get('E058_URL', 'http://localhost:8320'))
    p.add_argument('--db', default=os.environ.get('E058_DB', os.path.join(BASE, 'data.db')))
    p.add_argument('--no-endpoint', action='store_true', help='query SQLite directly')
    p.add_argument('--threshold-bps', type=float, default=20.0)
    p.add_argument('--last-n', type=int, default=4)
    p.add_argument('--sink', default=os.environ.get('E058_SINK', 'ntfy'),
                   choices=['ntfy', 'telegram'], help='notify channel (user=default ntfy)')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()

    d = get_rows(None if a.no_endpoint else a.endpoint, a.db, a.threshold_bps, a.last_n)
    key = '|'.join(d.get('snapshots', []))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    fresh = [r for r in d.get('rows', [])[:TOP_N] if state.get(r['coin']) != key]
    if not fresh:
        print('no new survivors (all alerted or none)');
        return
    lines = [f"e058 persistent funding ({key.split('|')[-1] if key else 'n/a'}):"]
    for r in fresh:
        lines.append(f"{r['coin']} {r['median_apy']:.0f}% APY "
                     f"long {r['long']} / short {r['short']} "
                     f"{r['persist']} flips {r['flips']} OI {r.get('oi_rank') or '500+'}")
    msg = '\n'.join(lines)
    if a.dry_run:
        print(msg);
        return
    if a.sink == 'ntfy':
        if send_ntfy(msg):
            for r in fresh: state[r['coin']] = key
            os.makedirs(os.path.dirname(STATE), exist_ok=True)
            json.dump(state, open(STATE, 'w'))
            print(f'ntfy sent {len(fresh)} survivors')
        else:
            sys.exit('ntfy send failed')
        return
    token, chat = os.environ.get('E058_TG_TOKEN'), os.environ.get('E058_TG_CHAT')
    if not token or not chat:
        sys.exit('missing E058_TG_TOKEN / E058_TG_CHAT (see ALERTS.md)')
    if send(token, chat, msg):
        for r in fresh: state[r['coin']] = key
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(state, open(STATE, 'w'))
        print(f'sent {len(fresh)} survivors')
    else:
        sys.exit('telegram send failed')

if __name__ == '__main__':
    main()
