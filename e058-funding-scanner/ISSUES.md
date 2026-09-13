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
(Status 2026-09-13: row tap no longer filters at all — tap opens a
coin detail with an explicit `filter to X` button + ✕. Deliberate
filtering lives in the filter box; mis-taps cost nothing.)

## 4. Title the main section (UX §3, fixed 2026-09-13 direct)

Shipped: `coins` title bar with live count + shared `.secttl` style +
coin detail card on row tap (full stats, paid record, explicit
filter/clear).

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

## 9. Alerts: digest-only (fixed 2026-09-13 direct, escalated same day)

Bug 1: dedup key was the snapshot window — persistent payers re-pinged
as URGENT every window slide (4 pings in 2h). First fix (24h re-ping
rule) worked mechanically (one silence logged) but three DIFFERENT
coins crossed within the hour — policy still wrong. Escalation: a
paper-stage scanner that cannot trade has no owner action attached to
any ping, so off-schedule pings are noise by definition. Now
digest-only (`off_schedule: false` in report_config.json): one ping/day
at 8 UTC, everything else silent. 24h new-payer rule stays as second
layer if ever re-enabled. Wording decoded: `e058 new payer/daily
funding digest` + `holding 4/4` + `(0 flips, OI rank 471)`.

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
