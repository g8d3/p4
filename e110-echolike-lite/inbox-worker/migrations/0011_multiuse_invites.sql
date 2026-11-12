-- An invite that works more than once.
--
-- One-use-only made the product wrong for its actual use: connecting two of my own
-- phones, or opening a space to three friends, meant a manual round trip per person and
-- a code that died on first use. `max_uses` (1..25) and a counter make one code do the
-- job for a group, while still expiring — and the owner can revoke it at any moment.
ALTER TABLE space_invites ADD COLUMN max_uses INTEGER NOT NULL DEFAULT 1;
ALTER TABLE space_invites ADD COLUMN uses INTEGER NOT NULL DEFAULT 0;
