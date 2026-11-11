-- One tenant (user) per claimed device. Everything is scoped by user_id.
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  ip TEXT,
  ua TEXT
);
CREATE TABLE IF NOT EXISTS devices (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  token_sha256 TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  last_seen TEXT,
  ip TEXT,
  ua TEXT
);
CREATE INDEX IF NOT EXISTS devices_user ON devices(user_id);
CREATE INDEX IF NOT EXISTS devices_ip ON devices(ip);
CREATE TABLE IF NOT EXISTS likes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  uid TEXT,
  kind TEXT,
  post_id TEXT,
  handle TEXT,
  url TEXT,
  text TEXT,
  clicked_at TEXT,
  ad INTEGER DEFAULT 0,
  received_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS likes_user ON likes(user_id, id DESC);
CREATE TABLE IF NOT EXISTS claims (ip TEXT NOT NULL, at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS claims_ip ON claims(ip, at);
CREATE TABLE IF NOT EXISTS usage (user_id TEXT NOT NULL, month TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (user_id, month));
