#!/usr/bin/env python3
"""Load funding captures into e058 SQLite. Idempotent (skips known timestamps)."""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if False else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import app as scanner

if __name__ == '__main__':
    for line in scanner.load_all():
        print(line)
    import sqlite3
    c = sqlite3.connect(scanner.DB)
    n = c.execute('SELECT COUNT(*) FROM funding').fetchone()[0]
    snaps = c.execute('SELECT COUNT(DISTINCT ts) FROM funding').fetchone()[0]
    print(f'total rows={n} snapshots={snaps} db={scanner.DB}')
