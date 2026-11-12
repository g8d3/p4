-- A diagnostics row needs counters, not just a status: "collected=30 sent=30
-- articles=48 scroller=DIV" answers what a 200 cannot. Same rule as the rest:
-- short, server-truncated, and never a capture's content.
ALTER TABLE telemetry ADD COLUMN detail TEXT;
