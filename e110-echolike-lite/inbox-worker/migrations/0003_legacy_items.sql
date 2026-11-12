-- v3.1: an old client (1.1.x) still queues plaintext items and has no way to
-- encrypt them, so the inbox accepts them and flags the row instead of dropping
-- the user's captures. A client that announces API >= 4 must send blobs.
ALTER TABLE likes ADD COLUMN legacy INTEGER DEFAULT 0;
