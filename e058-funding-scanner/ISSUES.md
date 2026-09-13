# e058 ISSUES — owner review 2026-09-13 (all logged in e062 ATTENTION.md)

Essence lives in `p4/e000-fundamentals/UX.md`. These are its instances.

## 1. Signals need their time window (UX §1)

Today: a signal says it survived N checks, not **from HH:MM to HH:MM,
how long, why it qualified**. Wanted: each signal carries
`present <start> → <end> (<duration>), <k>/<n> checks ≥ <thr> bps`.
The snapshot ts data already exists — render it. Deeper: think about
what ELSE time could say (first seen, longest hold, time since last
signal per coin) — the agent should propose more time measurements,
not just the one asked for.

## 2. `urgent if bigger ×` label (UX §7)

Today: `<label>urgent if bigger × <input></label>`. Meaning: outside
the 8 UTC digest hour, notify immediately only if spread ≥ threshold
× this multiplier (default 3×). Wanted: label that survives read-aloud,
e.g. `wake me anytime if spread ≥ [3]× threshold`. Behavior unchanged.

## 3. Filter must cover signals or say so (UX §3, §4)

Today: the coin filter filters the main table, silently skips the
signals section. Wanted: one rule — filter applies to every section
including signal history, or the filter names what it skips.

## 4. Title the main section (UX §3)

Top / filters / alerts / signals are named; the last (main) table
isn't. Wanted: a title (e.g. `coins`), so dev and user can point at it.

## 5. Align the config boxes (UX §5)

Today: scheduled-report inputs stacked one after another. Wanted:
aligned label/input grid. Same fix rolls to all apps.

## 7. Decode the top section (UX §8, fixed 2026-09-13 direct)

- `flippy — legs swapping` → `flippy — edge moves between LONG and
  SHORT` (server + JS, venues already on the row).
- `(new)` → `(no history yet)` (server, JS top line, table cell).
- Pulse line labeled: `data: 1317k rows, sample 9m ago every ~14m |
  backtest: 53.7% held 24h (102/190) | paper: 75 logged today,
  grades after 24h | version dbcbbd2` (`v` hash → `version`).
- `paper N logged` always says when grading happens; resolved
  scores read `(a/b graded)`.

## 9. Alerts: one ping per payer per day (fixed 2026-09-13 direct)

Bug: dedup key was the snapshot window, so every 15-min snapshot
re-pinged persistent payers as URGENT (4 pings in 2h on the owner's
phone). Rule: off-schedule pings are for NEW payers only — a coin
re-pings at most once per 24h; everything else waits for the 8 UTC
digest. Wording decoded too: `e058 new payer` + `holding 4/4` +
`(0 flips, OI rank 471)`. Legacy state entries re-ping once, then
silence. Progress, not every action.

## 8. Paper ballot section (UX §3, queued 2026-09-13)

Problem: the 75 predictions live only in SQLite; `/api/paper` serves
counts (plus first 5 names). The line reports a number about a list
nobody can open. Wanted: titled `paper ballot` section (not a tab —
mobile law: no new pages), containing: rules line (hit = spread still
≥ 20bps at first snapshot ≥ 24h after logging) + countdown to first
grade + score when resolved + ballot table (coin, entry APY/spread,
long→short, logged time, status grading-in-Xh → hit/miss), newest
first, scrollable, sticky header. Needs: one endpoint serving
paper_calls + paper_outcomes rows + section + e2e. Later: this section
IS the share page (UX §6) — same data, linkable.

## 6. Paper slip → share page (UX §6, bigger work)

Today: `copy paper slip` writes one line to clipboard (JS alert
fallback). Never used by the owner — sharing needs a **pretty page**:
record + history + curve, linkable. Wanted: per-coin/per-call share
view; keep the copy button until the page exists. Fleet-wide pattern,
start here.
