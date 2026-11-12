-- Accounts: identity for recovery, never a requirement to capture.
-- An account owns tenants (devices); it never sees plaintext. The key backup is
-- a blob wrapped with a passphrase-derived key, so this database can hand it back
-- but cannot open it.
CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS account_tokens (
  sha256 TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_seen TEXT
);
CREATE INDEX IF NOT EXISTS account_tokens_account ON account_tokens(account_id);
CREATE TABLE IF NOT EXISTS login_codes (
  account_id TEXT NOT NULL,
  code_sha256 TEXT NOT NULL,
  expires_at INTEGER NOT NULL,
  used INTEGER NOT NULL DEFAULT 0,
  ip TEXT
);
CREATE INDEX IF NOT EXISTS login_codes_account ON login_codes(account_id, expires_at);
CREATE TABLE IF NOT EXISTS account_tenants (
  account_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  linked_at TEXT NOT NULL,
  PRIMARY KEY (account_id, user_id)
);
CREATE TABLE IF NOT EXISTS key_backups (
  account_id TEXT PRIMARY KEY,
  salt TEXT NOT NULL,
  iterations INTEGER NOT NULL,
  iv TEXT NOT NULL,
  ct TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
