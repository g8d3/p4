#!/usr/bin/env python3
"""Import evidence/*.json tweet payloads into data/evidence.db (SQLite, stdlib only).
Run after bin/fetch.sh or any manual capture. Idempotent (INSERT OR REPLACE)."""
import json, glob, os, sqlite3
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "evidence.db")

def iso_ts(created):
  try:
    dt = datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y")
    return dt.date().isoformat(), dt.strftime("%H:%M")
  except Exception:
    return None, None

con = sqlite3.connect(DB)
con.execute("""CREATE TABLE IF NOT EXISTS tweets(
  id TEXT PRIMARY KEY, query TEXT, query_type TEXT, count INTEGER,
  captured TEXT, file TEXT, idx INTEGER, author TEXT, author_followers INTEGER,
  created_at TEXT, date TEXT, time_utc TEXT, text TEXT, url TEXT,
  likes INTEGER, reposts INTEGER, replies INTEGER, quotes INTEGER,
  bookmarks INTEGER, views INTEGER, lang TEXT, raw TEXT)""")
n = 0
for f in sorted(glob.glob(os.path.join(ROOT, "evidence", "*.json"))):
  d = json.load(open(f))
  ts = d.get("tweets", [])
  for i, t in enumerate(ts):
    a = t.get("author", {}) or {}
    iso, hm = iso_ts(t.get("created_at", ""))
    con.execute("""INSERT OR REPLACE INTO tweets VALUES
      (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
      str(t.get("id")), d.get("query"), d.get("queryType") or d.get("product"),
      d.get("count"), d.get("captured") or "2026-10-09", os.path.basename(f), i,
      (a.get("username") or ""), a.get("followers_count"), t.get("created_at"),
      iso, hm, t.get("text"), t.get("url"),
      t.get("favorite_count"), t.get("retweet_count"), t.get("reply_count"),
      t.get("quote_count"), t.get("bookmark_count"), t.get("view_count"),
      t.get("lang"), json.dumps(t)))
    n += 1
con.commit()
total = con.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]
print(f"imported {n} rows; db total {total}")
con.close()
