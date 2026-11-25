-- Ad reports: the rich version of a diagnostic.
--
-- The owner's rule, said out loud: "send enough data, fix privacy later". So a mark or
-- a "send what X shows" now carries the CARD'S OWN MARKUP (outerHTML, truncated) and
-- the actual short texts — a disclosure word this product has never seen, a CTA button,
-- a wrapper attribute — which is exactly what writing the next selector needs from a
-- phone with no devtools.
--
-- Limits that keep it a diagnostic and not a second inbox: one row per press, body
-- capped at 128 KB, html at 96 KB, detail at 2 KB, words at 1 KB, tied to the tenant
-- that sent it (so nobody reads anybody else's), and never written to `likes`.
CREATE TABLE IF NOT EXISTS ad_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  user_id TEXT,
  version TEXT,
  kind TEXT,          -- 'mark' (a card the owner tapped) or 'report' (a whole timeline)
  post_url TEXT,
  detail TEXT,        -- the compact structure line
  words TEXT,         -- the short texts, as they are (privacy later, by owner's order)
  html TEXT           -- the card's / timeline's outerHTML, truncated
);
CREATE INDEX IF NOT EXISTS ad_reports_at ON ad_reports(at DESC);
CREATE INDEX IF NOT EXISTS ad_reports_user ON ad_reports(user_id, id DESC);
