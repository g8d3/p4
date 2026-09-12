#!/usr/bin/env python3
"""e058 Telegram alerts for persistent funding spreads.
Reads /api/persistence (or --db directly), sends top survivors via Bot API.
Secrets ONLY from env: E058_TG_TOKEN, E058_TG_CHAT. Never commit them.
State: data/alert_state.json (git-ignored) skips already-alerted windows.
Test (dry run, no Telegram call):  python3 bin/alert.py --dry-run"""
import json, os, sqlite3, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BASE, 'data', 'alert_state.json')
CFG_PATH = os.path.join(BASE, 'report_config.json')
CFG_DEFAULTS = {'report_hour_utc': 8, 'threshold_bps': 50.0, 'last_n': 4,
                'top_n': 10, 'urgent_mult': 3.0}

def load_cfg():
    cfg = dict(CFG_DEFAULTS)
    try:
        user = json.load(open(CFG_PATH))
        for k in cfg:
            if k in user:
                cfg[k] = user[k]
    except Exception:
        pass
    return cfg

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
        data=urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get('ok', False)

def log_to_site(endpoint, window, rows):
    """Persist sent signals to the website history (best-effort, never fatal)."""
    try:
        body = json.dumps({'window': window, 'rows': rows}).encode()
        req = urllib.request.Request(f'{endpoint}/api/signals/log', data=body,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r).get('ok', False)
    except Exception as e:
        print(f'signal-log warn: {str(e)[:100]}')
        return False

def send_ntfy(text, title='e058 funding'):
    import os
    topic = os.environ.get('NTFY_TOPIC')
    if not topic:
        sys.exit('missing NTFY_TOPIC env')
    server = os.environ.get('NTFY_SERVER', 'https://ntfy.sh').rstrip('/')
    req = urllib.request.Request(f'{server}/{topic}', data=text.encode(),
        headers={'Title': title, 'Priority': 'default', 'Tags': 'chart_with_upwards_trend'},
        method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status in (200, 202)

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--endpoint', default=os.environ.get('E058_URL', 'http://localhost:8320'))
    p.add_argument('--db', default=os.environ.get('E058_DB', os.path.join(BASE, 'data.db')))
    p.add_argument('--no-endpoint', action='store_true', help='query SQLite directly')
    p.add_argument('--threshold-bps', type=float, default=None,
                   help='override report_config.json threshold')
    p.add_argument('--last-n', type=int, default=None,
                   help='override report_config.json last_n')
    p.add_argument('--top-n', type=int, default=None,
                   help='override report_config.json top_n')
    p.add_argument('--force', action='store_true',
                   help='send full digest now, ignoring the scheduled hour')
    p.add_argument('--sink', default=os.environ.get('E058_SINK', 'ntfy'),
                   choices=['ntfy', 'telegram'], help='notify channel (user=default ntfy)')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    cfg = load_cfg()
    threshold = a.threshold_bps if a.threshold_bps is not None else float(cfg['threshold_bps'])
    last_n = a.last_n if a.last_n is not None else int(cfg['last_n'])
    top_n = a.top_n if a.top_n is not None else int(cfg['top_n'])
    urgent_cut = threshold * float(cfg['urgent_mult'])
    hour = datetime.now(timezone.utc).hour
    digest_due = (hour == int(cfg['report_hour_utc'])) or a.force

    d = get_rows(None if a.no_endpoint else a.endpoint, a.db, threshold, last_n)
    window = d.get('snapshots', [])
    key = '|'.join(window)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    fresh = [r for r in d.get('rows', [])[:top_n] if state.get(r['coin']) != key]
    if not fresh:
        print('no new survivors (all alerted or none)');
        return
    if not digest_due and not a.dry_run:
        urgent = [r for r in fresh if (r.get('spread_bps') or 0) >= urgent_cut]
        if not urgent:
            print(f'digest deferred to {int(cfg["report_hour_utc"]):02d}:00 UTC '
                  f'({len(fresh)} non-urgent survivors, cutoff {urgent_cut:.0f} bps)');
            return
        fresh = urgent
        print(f'off-schedule: {len(fresh)} URGENT survivors (>= {urgent_cut:.0f} bps)')
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
            logged = log_to_site(a.endpoint, window, fresh)
            print(f'ntfy sent {len(fresh)} survivors (site-logged={logged})')
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
        logged = log_to_site(a.endpoint, window, fresh)
        print(f'sent {len(fresh)} survivors (site-logged={logged})')
    else:
        sys.exit('telegram send failed')

if __name__ == '__main__':
    main()
