-- One capture, one row. Before this, a re-send (a retry, or the repair pass that
-- compares the browser with the inbox) inserted the same capture again: 45 extra
-- rows and 45 units of quota in one afternoon, and the duplicates pushed the real
-- captures out of the read window. Clean up what exists, then make it impossible.
DELETE FROM likes
 WHERE uid IS NOT NULL
   AND id NOT IN (SELECT MIN(id) FROM likes WHERE uid IS NOT NULL GROUP BY user_id, uid);

CREATE UNIQUE INDEX IF NOT EXISTS likes_user_uid ON likes(user_id, uid) WHERE uid IS NOT NULL;

-- The quota is a count of stored captures: put it back in line with the table so
-- the deleted duplicates stop charging the user for rows that no longer exist.
UPDATE usage
   SET n = (SELECT COUNT(*) FROM likes l WHERE l.user_id = usage.user_id)
 WHERE month = strftime('%Y-%m', 'now');

-- Reads walk the whole list in pages now: (user_id, id DESC) already covers it,
-- so nothing else is needed here.
