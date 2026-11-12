-- Shared spaces: the collaborative unit. A capture can belong to a space (visible to
-- every member) instead of only to the tenant that made it. Membership is per tenant
-- (a device), and joining is by invitation: a one-time, expiring token — never a shared
-- permanent secret, which cannot be rotated and cannot be revoked one member at a time.
CREATE TABLE IF NOT EXISTS spaces (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS space_members (
  space_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'member', -- owner (can revoke) | member
  joined_at TEXT NOT NULL,
  PRIMARY KEY (space_id, user_id)
);
CREATE INDEX IF NOT EXISTS space_members_user ON space_members(user_id);

CREATE TABLE IF NOT EXISTS space_invites (
  id TEXT PRIMARY KEY,
  space_id TEXT NOT NULL,
  sha256 TEXT NOT NULL UNIQUE,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at INTEGER NOT NULL,
  used_by TEXT,
  used_at TEXT
);
CREATE INDEX IF NOT EXISTS space_invites_space ON space_invites(space_id, expires_at);

-- NULL = a personal capture (today's behaviour); a value = shared with that space.
ALTER TABLE likes ADD COLUMN space_id TEXT;
CREATE INDEX IF NOT EXISTS likes_space ON likes(space_id, id DESC);
