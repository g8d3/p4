#!/usr/bin/env python3
"""e062 ops bus: events + heartbeats + rungs + staleness. SQLite only."""
import os, sqlite3, sys, time

DB = os.environ.get('E062_DB', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ops.db'))

SCHEMA = """
CREATE TABLE IF NOT EXISTS events(ts INTEGER, track TEXT, kind TEXT, summary TEXT, dedup_key TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS heartbeats(track TEXT PRIMARY KEY, ts INTEGER, status TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS rungs(track TEXT PRIMARY KEY, rung INTEGER, ts INTEGER, url TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS ledger(ts INTEGER, track TEXT, kind TEXT, usd REAL, note TEXT);
CREATE TABLE IF NOT EXISTS trials(name TEXT PRIMARY KEY, ts INTEGER, renews_ts INTEGER, cost_usd REAL, status TEXT DEFAULT 'active', note TEXT);
CREATE TABLE IF NOT EXISTS paused(track TEXT PRIMARY KEY, ts INTEGER, reason TEXT);
CREATE TABLE IF NOT EXISTS notes(ts INTEGER, track TEXT, message TEXT, done INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS proposals(id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, track TEXT, amount_usd REAL, action TEXT, reason TEXT, status TEXT DEFAULT 'pending', decided_ts INTEGER);
"""

def db():
    c = sqlite3.connect(DB)
    c.executescript(SCHEMA)
    return c

def init():
    db().close()
    print(f'ops.db ready at {DB}')

def fmt_owner_tech_reminder(track, note, where):
    # OWNER-FIRST REPORTING (owner law 2026-09-12): every beat/event ships as
    # `OWNER_SENTENCE | tech: detail`. Board simple-mode shows only the plain
    # half, so jargon-only notes fail the <30s phone test. Warn, don't crash
    # (cron/healthcheck paths must never break on a missing separator).
    if note and ' | ' not in str(note) and track not in ('runner',):
        print(f'OWNER-FIRST reminder [{where} {track}]: note has no " | " separator — '
              f'write "<plain phone sentence> | tech: <detail>" so simple mode stays readable.',
              file=sys.stderr)

def emit(track, kind, summary, dedup=None):
    fmt_owner_tech_reminder(track, summary, 'emit')
    c = db()
    try:
        c.execute('INSERT INTO events VALUES (?,?,?,?,?)',
                  (int(time.time()), track, kind, summary, dedup or summary))
        c.commit()
        print('emitted')
    except sqlite3.IntegrityError:
        print('duplicate (dedup hit)')
    c.close()

def beat(track, status='ok', note=''):
    fmt_owner_tech_reminder(track, note, 'beat')
    c = db()
    c.execute('INSERT OR REPLACE INTO heartbeats VALUES (?,?,?,?)',
              (track, int(time.time()), status, note))
    c.commit(); c.close()
    print(f'heartbeat {track}={status}')

def promote(track, rung, url='', note=''):
    # Swap guard (2026-09-12: a leg passed e059's note as url and url as note,
    # breaking the board link). The URL is whichever arg looks like one.
    if url and not url.startswith(('http://', 'https://')) and note.startswith(('http://', 'https://')):
        url, note = note, url
    c = db()
    cur = c.execute('SELECT rung FROM rungs WHERE track=?', (track,)).fetchone()
    if cur and cur[0] >= rung:
        print(f'already rung {cur[0]}'); c.close(); return
    c.execute('INSERT OR REPLACE INTO rungs VALUES (?,?,?,?,?)',
              (track, rung, int(time.time()), url, note))
    c.commit(); c.close()
    print(f'{track} -> rung {rung}')
    emit(track, 'promote', f'{track} reached rung {rung}: {note or url}', dedup=f'{track}:rung:{rung}')

def propose(track, amount, action, reason):
    c = db()
    cur = c.execute('INSERT INTO proposals(ts, track, amount_usd, action, reason) VALUES (?,?,?,?,?)',
                    (int(__import__('time').time()), track, float(amount), action, reason))
    pid = cur.lastrowid
    c.commit(); c.close()
    print(f'proposal #{pid} recorded (pending)')
    emit(track, 'proposal', f'#{pid} ${amount}: {action} — {reason}', dedup=f'proposal:{pid}')

def decide(pid, verdict):
    assert verdict in ('approved', 'rejected', 'executed')
    c = db()
    c.execute("UPDATE proposals SET status=?, decided_ts=? WHERE id=?",
              (verdict, int(__import__('time').time()), int(pid)))
    c.commit(); c.close()
    print(f'#{pid} -> {verdict}')

def proposals(status='pending'):
    c = db()
    rows = c.execute('SELECT id, datetime(ts,"unixepoch"), track, amount_usd, action, reason, status FROM proposals WHERE status=? ORDER BY id', (status,)).fetchall()
    c.close()
    for r in rows: print(r)
    if not rows: print('(none)')

def trial(name, renews, cost=0.0, note=''):
    import time as t, datetime as dt
    try: rts = int(dt.datetime.fromisoformat(renews).timestamp())
    except Exception: sys.exit('renews must be YYYY-MM-DD')
    c = db()
    c.execute('INSERT OR REPLACE INTO trials VALUES (?,?,?,?,?,?)',
              (name, int(t.time()), rts, float(cost), 'active', note))
    c.commit(); c.close()
    print(f'trial {name} renews {renews} (${cost})')

def trials(days=7):
    import time as t
    c = db()
    rows = c.execute("SELECT name, datetime(renews_ts,'unixepoch'), cost_usd, status, note FROM trials WHERE status='active' ORDER BY renews_ts").fetchall()
    c.close()
    now = int(t.time())
    for n, rd, co, st, no in rows:
        c2 = db()
        rts = c2.execute('SELECT renews_ts FROM trials WHERE name=?', (n,)).fetchone()[0]
        c2.close()
        left = (rts - now) // 86400
        flag = ' <-- DUE' if left <= days else ''
        print(f'{n} renews {rd} ${co} ({left}d left) {no}{flag}')
    if not rows: print('(no active trials)')

def spend(track, usd, note=''):
    c = db()
    c.execute('INSERT INTO ledger VALUES (?,?,?, ?,?)' if False else 'INSERT INTO ledger VALUES (?,?,?,?,?)',
              (int(__import__('time').time()), track, 'spend', float(usd), note))
    c.commit(); c.close()
    print(f'spent ${usd} [{track}] {note}')

def earn(track, usd, note=''):
    c = db()
    c.execute('INSERT INTO ledger VALUES (?,?,?,?,?)',
              (int(__import__('time').time()), track, 'earn', float(usd), note))
    c.commit(); c.close()
    print(f'earned ${usd} [{track}] {note}')

def runway(budget=300.0):
    c = db()
    sp = c.execute("SELECT COALESCE(SUM(usd),0) FROM ledger WHERE kind='spend'").fetchone()[0]
    ea = c.execute("SELECT COALESCE(SUM(usd),0) FROM ledger WHERE kind='earn'").fetchone()[0]
    c.close()
    print(f'spent ${sp:.2f} earned ${ea:.2f} net ${ea-sp:.2f} | budget ${budget:.2f} left ${budget-sp+ea:.2f}')
    c = db()
    for r in c.execute("SELECT track, kind, SUM(usd), COUNT(*) FROM ledger GROUP BY track, kind ORDER BY track"):
        print(r)
    c.close()

def note(track, message):
    import time as t
    c = db()
    c.execute('INSERT INTO notes VALUES (?,?,?,0)', (int(t.time()), track, message))
    c.commit(); c.close()
    print(f'note -> {track}')

def inbox(track=None, limit=10):
    c = db()
    q = 'SELECT datetime(ts,"unixepoch"), track, message, done FROM notes'
    args = []
    if track:
        q += ' WHERE track=?'; args.append(track)
    q += ' ORDER BY ts DESC LIMIT ?'; args.append(int(limit))
    for r in c.execute(q, args): print(r)
    c.close()

def ack(track, n='all'):
    # Inbox hygiene: mark owner notes consumed-and-shipped as done so the
    # waiting badge never nags for finished work. Never ack unshipped work.
    import time as t
    c = db()
    if str(n).lower() == 'all':
        cur = c.execute('UPDATE notes SET done=1 WHERE track=? AND done=0', (track,))
    else:
        cur = c.execute('UPDATE notes SET done=1 WHERE rowid IN (SELECT rowid FROM notes WHERE track=? AND done=0 ORDER BY ts DESC LIMIT ?)',
                        (track, int(n)))
    c.commit()
    left = c.execute('SELECT COUNT(*) FROM notes WHERE track=? AND done=0', (track,)).fetchone()[0]
    c.close()
    print(f'acked {cur.rowcount} [{track}], {left} still open')

def pause(track, reason='owner'):
    import time as t
    c = db()
    c.execute('INSERT OR REPLACE INTO paused VALUES (?,?,?)', (track, int(t.time()), reason))
    c.commit(); c.close()
    print(f'paused {track}')

def resume(track):
    c = db()
    c.execute('DELETE FROM paused WHERE track=?', (track,))
    c.commit(); c.close()
    print(f'resumed {track}')

def paused_list():
    c = db()
    rows = c.execute('SELECT track FROM paused').fetchall()
    c.close()
    return [r[0] for r in rows]

def stale(max_age_h=49):
    import time as t
    c = db()
    now = int(t.time())
    rows = c.execute('SELECT track, ts, status, note FROM heartbeats').fetchall()
    c.close()
    dead = [(tr, (now - ts) // 3600) for tr, ts, st, no in rows if now - ts > max_age_h * 3600]
    if not dead:
        print('all tracks alive')
    for tr, h in dead:
        print(f'STALE {tr} silent {h}h')
    return dead

def status():
    c = db()
    print('-- rungs --')
    for r in c.execute('SELECT track, rung, datetime(ts,"unixepoch"), url, note FROM rungs'):
        print(r)
    print('-- heartbeats --')
    for r in c.execute('SELECT track, datetime(ts,"unixepoch"), status, note FROM heartbeats'):
        print(r)
    print('-- paused --')
    print(paused_list())
    print('-- inbox (owner -> project) --')
    for r in c.execute("SELECT datetime(ts,'unixepoch'), track, message FROM notes WHERE done=0 ORDER BY ts DESC LIMIT 10"):
        print(r)
    print('-- recent events --')
    for r in c.execute('SELECT datetime(ts,"unixepoch"), track, kind, summary FROM events ORDER BY ts DESC LIMIT 15'):
        print(r)
    c.close()

CMDS = {'init': lambda a: init(), 'emit': lambda a: emit(*a),
        'propose': lambda a: propose(*a), 'decide': lambda a: decide(*a),
        'trial': lambda a: trial(*a), 'trials': lambda a: trials(int(a[0]) if a else 7),
        'note': lambda a: note(a[0], ' '.join(a[1:])),
        'pause': lambda a: pause(*a),
        'ack': lambda a: ack(*a),
        'resume': lambda a: resume(a[0]),
        'inbox': lambda a: inbox(*(a or [])),
        'spend': lambda a: spend(*a), 'earn': lambda a: earn(*a),
        'runway': lambda a: runway(float(a[0]) if a else 300.0),
        'proposals': lambda a: proposals(*a),
        'beat': lambda a: beat(*a), 'promote': lambda a: promote(a[0], int(a[1]), *(a[2:])),
        'stale': lambda a: stale(int(a[0]) if a else 49), 'status': lambda a: status()}

if __name__ == '__main__':
    CMDS['pending'] = CMDS['proposals']
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        sys.exit('usage: ops.py {init|emit|beat|promote|stale|status|propose|decide|proposals|ack} ...')
    CMDS[sys.argv[1]](sys.argv[2:])
