# BookmarkVault extension stub (v0.1.0)

Local-first MV3 extension. No build step, no secrets.

## Load
1. Open `chrome://extensions`, enable Developer mode.
2. Load unpacked → this `ext/` folder.
3. Open `x.com/i/bookmarks` or `x.com/i/history`, click the BookmarkVault action to open the side panel.

## What works now
- Dual capture on the bookmarks page: XHR hook (primary, `source: xhr`) + DOM fallback (`source: dom`, XHR wins on conflict).
- Local queue in `chrome.storage.local` (capped at 2000). Badge shows queue size.
- Side panel: Saved (server search + label filter, Clear button, local-time dates, Open link, no-scroll refresh) / Labels (create, counts, filter) / Sync (API base + token, sync now, risk score, plan card) / Hooks (outbound webhook URLs) / Export (JSON download, includes labels).
- Sync tab shows plan/entitlement: reads GET /v1/billing/me with your base + token (Check plan button, auto-loads). No token → "Free (local-only)". Unreachable → "unknown, staying local-only".
- Labels tab: create via POST /v1/labels, list via GET /v1/labels (merged with local defs). Per bookmark: attach via POST /v1/bookmarks/:id/labels, detach via DELETE. No API base + token → everything stays on this device and syncs later.
- Background worker: 15-min alarm retry, rate-limit backoff, resilience gate (pause >70, slow 40–70).
- No token configured → stays local-only. Nothing leaves the device.

## Store listing (v0.11-store)
- `ext/store/listing.md`: paste-ready Name, Short (132 chars), Long description, Category Productivity, permissions justification, publish checklist. English only.
- `ext/store/screenshots/01-saved-1280.png 02-sync-1280.png 03-labels-1280.png`: real-Chrome 1280x800 shots of the same verified panes (390px proofs in loop/proof/leg-19/).
- Icons redrawn per size (navy bookmark glyph): icon16/icon48/icon128.png.
- Publish waits only on your domain (privacy/support URLs) — no merchant keys needed for the listing itself.

## Still stubbed
- `/v1/bookmarks/import` upload target exists in backend stub (in-memory, port 8899) — sync works against it.
- Hooks tab: add https:// URLs locally, registers via POST /v1/webhooks/bookmarks, lists via GET (merged with local).
