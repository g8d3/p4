# ONE_TABLE — one entity, one table

Status: shared convention (opt-in via `## Inherits`, one line per project).
No copies: projects link here, they never duplicate this file.

## The problem

Agents answer every new question with a NEW table instead of adding
columns or a view to the table the entity already has. The result is
table sprawl: the same rows in two or more places, copies that diverge,
and a user forced to hunt across tables for one fact. It is always
annoying and often wrong.

## The rule

One entity (or event stream) gets exactly ONE table, named by its grain:
**one row = one X** (one opportunity, one ledger event, one worker).
Every new question about X is answered with a column, a filter, or a
saved view over that table — never with a second table.

## Violations (each one is a bug, fix by merging)

1. **Same grain, two tables.** Two tables where one row means the same
   thing (e.g. `gates` and `opportunities` both being "one opportunity").
   Merge: keep one, move the other's columns over (NULL/— allowed).
2. **Filter-copy.** Table B is a subset, sort, or top-N of table A
   (e.g. "needs-you" rows that already exist in `opportunities`).
   That is a VIEW (preset chip / filter state), not a table. Views never
   duplicate rows — they are filter state over the same rows.
3. **1:1 keys.** Two tables share the key column and their rows match
   one-to-one (e.g. `coins` + `coin_notes` keyed by token). Those are
   columns of one table, not two tables.
4. **Table-per-value.** One table per status, source, priority, or track
   (`watch_high` / `watch_low`, `bounties` / `gigs`). The varying value
   is a COLUMN (`signal`, `source`, `track`); the per-value cut is a VIEW.
5. **Parallel tables.** Two tables with no shared key, joined only by
   row order or by the reader's memory. Give them one key or merge them.

## Legal splits (the only reasons for two tables)

- **Different grain.** Events vs aggregates over those events
  (`ledger` rows vs `funds` KPIs). One row means something different —
  that is two entities, two tables.
- **Different write owner / lifecycle.** Append-only machine log vs
  curated human dimension (`watch.jsonl` sightings vs `resources`).
- **Visibility boundary.** What the user may see vs internal scratch.
- **Same grain, many sources.** Merge with UNION into one table
  (one `opportunities` from watch + candidates) — never one table
  per source.

Anything else that wants to be a second table needs a written reason
in the decision log. "It was easier" is not a reason.

## The test (ask in order, before creating any table)

1. Does a table with this grain already exist? **Yes → merge.**
2. Is what I want a subset/sort/ranking of an existing table?
   **Yes → VIEW** (preset chip, filter, sort — zero new rows).
3. Do my rows match an existing table's keys 1:1?
   **Yes → add columns.**
4. Otherwise: name the grain in one sentence ("one row = one …").
   If you cannot, you do not need a table yet.

## Checks (automatable in review)

- Two tables share a key column name → suspect violation 3.
- Row-key overlap > 80% between tables → suspect violation 1.
- Every row of B is contained in A → B is a filter-copy (violation 2).
- A table name containing a value another table has as a column
  (`watch_high` vs `signal=high`) → violation 4.

## Migration recipe

Surviving table + missing columns (NULL/— ok) → point every reader
at a filter/view → delete the duplicate → log the merge as a decision.
One table, many views, zero copies.
