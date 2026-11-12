-- Discovery: two strangers with the same interests, found by the system.
--
-- A code only works when you already know who to give it to. So:
--   * each device registers an ECDH P-256 public key (the private half never leaves it);
--   * an opted-in user publishes a BLIND index of what they saved: sha256 of kind|post id.
--     Never text, never a handle, never the post id itself. The server can group equal
--     hashes across users and count overlaps; it cannot read what a hash is without
--     enumerating X's public ids, which is the documented limit and the reason this is
--     opt-in and easy to switch off (turning it off deletes the rows).
--   * an invitation can therefore be ADDRESSED to a user: the space key is wrapped to
--     their device public key (ECDH + HKDF + AES-GCM, in the browser), so the server
--     stores a box it cannot open and nobody has to send anybody a code.
ALTER TABLE devices ADD COLUMN ecdh_pub TEXT;

CREATE TABLE IF NOT EXISTS discovery_opt (
  user_id TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interest (
  h TEXT NOT NULL,
  user_id TEXT NOT NULL,
  at TEXT NOT NULL,
  PRIMARY KEY (h, user_id)
);
CREATE INDEX IF NOT EXISTS interest_user ON interest(user_id);

ALTER TABLE space_invites ADD COLUMN for_user TEXT;
ALTER TABLE space_invites ADD COLUMN wrapped TEXT;
CREATE INDEX IF NOT EXISTS space_invites_target ON space_invites(for_user, expires_at);
