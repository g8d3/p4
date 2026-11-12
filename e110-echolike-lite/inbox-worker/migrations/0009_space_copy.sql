-- A capture can live in two places at once: in your personal list AND in a space you
-- share it with. The old unique index (user_id, uid) made those the same row, so
-- sharing your own capture was silently ignored (INSERT OR IGNORE) and the space never
-- got it. One index per home:
--   * personal rows: one per (tenant, uid)
--   * space rows:    one per (space, uid) -- sharing the same uid to two spaces is fine
DROP INDEX IF EXISTS likes_user_uid;
CREATE UNIQUE INDEX IF NOT EXISTS likes_personal_uid ON likes(user_id, uid) WHERE space_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS likes_space_uid ON likes(space_id, uid) WHERE space_id IS NOT NULL;
