# leg-21 proof — saved-search relevance (newest-first + dupe highlight)

## What changed
- `ext/sidepanel/sidepanel.js` `render()`: both local and server-merged
  paths now sort by `created_at` (fallback `queued_at`/`imported_at`)
  descending — previously local used insertion order (`.slice(-100).reverse()`).
- Same-text duplicates (normalized: lowercase, URLs stripped, whitespace
  folded, min 20 chars) get a `Possible duplicate ×N` badge in the item
  meta row; the status line adds `· newest first` and
  `· N possible duplicate(s)`.
- `ext/sidepanel/index.html`: `.dupe` badge CSS (amber, wraps with meta row).

## Verification (not claimed: checked)
- `node --check` clean; extracted sort/dupe logic unit-tested in node:
  order b,c,a newest-first OK, same-text ×2 detected, unrelated text ignored.
- `loop/trial-check.py`: 100/100, static green.
- Hub + sidepanel + landing serve 200 over local http.
- Real Chrome 390px: `sidepanel-390.png` eyeballed — single-row 5-tab bar,
  no wrap/overflow, bottom bar visible on first paint, English-only empty
  state. `hub-390.png` (cycle.html over plain http shows its no-backend
  empty state; unchanged by this leg, bottom bar intact).
- Console check (`--enable-logging=stderr`, grep CONSOLE/Uncaught): no hits.

## First-30-seconds dogfood
- Fresh open: "0 saved locally", search + Clear + label filter, empty-state
  hint. Confirmation of work: after capturing, newest item is on top and any
  re-saved same-text item carries a visible "Possible duplicate ×2" badge —
  the confirmation ships with the feature.

## Verdict
Presentable: no layout regression at 390px, no console errors, trial 100/100.
Dupe badge itself not screenshotable in the empty http state (needs seeded
bookmarks); logic covered by the node unit check above.
