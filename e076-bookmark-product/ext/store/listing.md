# BookmarkVault — Chrome Web Store listing (draft, v0.11-store)

All user-facing text in English. No keys needed to publish the draft;
production URLs/keys stay human-gated (see ops/needs.json).

## Name (max 75 chars)
BookmarkVault — local-first X-bookmark backup

## Short description (max 132 chars, shown in search)
Back up your X bookmarks on this device while you browse. Labels, search, export. No auto-scroll.

## Long description (store "Description" field)
Back up your X bookmarks without handing them to a cloud first.

BookmarkVault is local-first: while YOU browse x.com/i/bookmarks, it
saves what you already see into this device — nothing runs in hidden
tabs, nothing scrolls for you, nothing leaves the device until you say so.

What you get:
- Automatic capture while you browse (network hook first, page text as fallback; the network copy wins on conflict, each item tagged with its source).
- Saved list with full-text search, label filter, local-time dates, and one-tap Open on the original post.
- Labels: create, filter, attach and detach per bookmark.
- Sync tab: optional backup to your own server (API base + token), queue count, risk notice that slows or pauses when X rate-limits, plus your plan (Free local-only without a token).
- Hooks: register your own https:// webhook URLs for new imports.
- Export: one-click JSON download including labels.
- Approvals: propose an action, then approve or reject it. Risky steps wait as pending.

Privacy:
- Local-first. Without an API base + token, everything stays on this device.
- No background scraping. Pagination = you scroll; the extension only observes.
- If X answers 429 or a captcha, BookmarkVault backs off for 10 minutes and tells you plainly.
- Permissions used: storage (your queue on this device), alarms (retry timer), sidePanel (the panel), host access to x.com/twitter.com (read bookmarks you open) and to your configured API base (sync only).

Pricing: Free local-only. Paid backup plans (Monthly $7/mo, Yearly $99/yr, Lifetime $198 one-time) unlock server backup; billing runs in test mode until the owner wires production keys. Support: see landing Contact page.

## Category / language
Category: Productivity. Language: English (en).

## Icons (in ext/icons/, MV3)
- icon16.png — 16x16 toolbar/favicon.
- icon48.png — 48x48 extension management page.
- icon128.png — 128x128 store + install dialog.
- Design: navy (#1B436E) square, white bookmark card with notch, three navy lines. Same glyph at all sizes, redrawn per size (no downscale blur).

## Screenshots (in ext/store/screenshots/, 1280x800, real Chrome)
1. `01-saved-1280.png` — Saved pane: search + label filter + Open links.
2. `02-sync-1280.png` — Sync pane: queue count, plan card, proposed actions.
3. `03-labels-1280.png` — Labels pane: create + filter + attach chips.
Source panes verified at 390px in loop/proof/leg-19/ (presentable v0.10-tabs); these 1280px shots are the same pages reframed for the store (no behavior change).

## Permissions justification (paste into store "Permissions" notes)
- storage: local bookmark queue + labels + settings on this device.
- alarms: 15-minute sync-retry timer only.
- sidePanel: the Saved/Labels/Sync/Hooks/Export panel.
- Host x.com, twitter.com: read bookmark data on pages the user opens. No background tabs, no auto-scroll.
- Host http://127.0.0.1, http://localhost, https://*: user-configured API base for optional backup sync only.

## Privacy / support links (human-gated placeholders flagged)
- Privacy policy URL: landing privacy.html (ships in repo; public URL waits on owner domain).
- Support URL: landing contact.html (email is a documented placeholder until owner provides one).
- No data is sold. Local-only by default; server sync only with the user's own token.

## Publish checklist (owner, ~10 min)
1. Zip ext/ (manifest + icons + sidepanel). Version in manifest.json must match VERSION.
2. developer.chrome.com → new item → upload zip → paste Name/Short/Long from this file.
3. Upload icons (128 required) + the 3 screenshots from screenshots/.
4. Set Category Productivity, Language English, Privacy + Support URLs after domain is live.
5. Submit for review. No merchant keys needed for the listing itself.
