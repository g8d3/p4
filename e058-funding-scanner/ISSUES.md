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

## 6. Paper slip → share page (UX §6, bigger work)

Today: `copy paper slip` writes one line to clipboard (JS alert
fallback). Never used by the owner — sharing needs a **pretty page**:
record + history + curve, linkable. Wanted: per-coin/per-call share
view; keep the copy button until the page exists. Fleet-wide pattern,
start here.
