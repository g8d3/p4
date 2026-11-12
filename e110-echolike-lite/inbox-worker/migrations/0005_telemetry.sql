-- Diagnostics: what a button press did, never what it captured.
-- Whitelisted fields only (action, ok, http code, ms, error text, version, host),
-- so a capture's text, handle or url can never land here.
CREATE TABLE IF NOT EXISTS telemetry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  ip_hash TEXT,
  user_id TEXT,
  version TEXT,
  action TEXT NOT NULL,
  ok INTEGER,
  code INTEGER,
  ms INTEGER,
  host TEXT,
  error TEXT
);
CREATE INDEX IF NOT EXISTS telemetry_at ON telemetry(at DESC);
CREATE INDEX IF NOT EXISTS telemetry_user ON telemetry(user_id, id DESC);
