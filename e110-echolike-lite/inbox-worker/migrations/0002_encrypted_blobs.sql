-- v3: the extension encrypts each capture in the browser and uploads an opaque
-- blob. The old readable columns stay (nullable) so a v2 client keeps working,
-- but nothing new is written to them.
ALTER TABLE likes ADD COLUMN iv TEXT;
ALTER TABLE likes ADD COLUMN ct TEXT;
ALTER TABLE likes ADD COLUMN bytes INTEGER;
