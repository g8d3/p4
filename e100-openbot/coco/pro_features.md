# EchoLike Pro — feature candidates (from extension v2.7.0 code review)

Sources: `extension_echolike/` content.js (275 ln), background.js (187 ln), popup.js (141 ln), options.js (41 ln), manifest.json, README.md. Times in Bogotá (UTC-5). Nothing invented beyond the code and site copy.

## What is free today (v2.7.0)
No gating or Pro flag exists anywhere in the code — everything currently shipped is free:
- Like / unlike / bookmark / remove-bookmark capture on x.com (content.js `ACCIONES`), with tweet text, handle, URL and time extracted.
- 🎙 Voice note (max 60 s) next to the like; written note via long-press on the heart (HOLD_MS=500), **N** within 5 s (N_MS=5000), or the ✎ hover button.
- **B** keyboard shortcut to bookmark (X has none).
- Local-first storage in browser `storage.local` (unlimitedStorage), JSON export/import backup from options.
- Opt-in sync: AES-256-GCM encrypted events through a secret ntfy.sh topic to the EchoLike inbox (background.js `cifrar`/`publicar`); pair code `EL2|server|topic|key`.
- Popup: daily like/bookmark counter, recent-events table (trimmed to the 20 most recent events via MAXEV — a display cap only, not a queue/failure cap on outgoing events, which live in a separate unbounded `cola` list), failure badge, connection status.
- Update channel via echolike.app (`extension_update.json`), CRX for Android/Quetta.

## Pro feature candidates

### 1. Unlimited-length voice notes + automatic transcription
Free caps voice at 60 s; transcription happens server-side in the existing pipeline (`stt.py`). Pro: remove the cap, searchable text transcripts in the private Today view, EN↔ES translation.
**Effort:** medium — ~1–2 weeks (recording logic + STT/translation quota).
**Local-first:** mostly — audio recorded locally; transcription needs a server; notes stay local until opt-in sync.

### 2. Collections, tags and full-text search
Saved posts sit in a flat `datos` array (popup.js). Pro: tag/categorise saved posts, themed collections (the free build already hints at "likes in themes"), search across text, notes and transcripts.
**Effort:** medium-high — ~2–3 weeks (new data model + migration, popup/options UI, private-page views).
**Local-first:** yes — all in browser storage; sync only encrypts and mirrors.

### 3. Automatic backup & multi-device sync
Today sync pushes events one way to one inbox; no two-way sync or scheduled backup. Pro: scheduled encrypted backups (JSON), restore on a new device, true multi-device merge.
**Effort:** medium — ~2 weeks (the `alarms` permission is already in the manifest; merge logic is the hard part).
**Local-first:** yes — transport is end-to-end encrypted; the server never sees plaintext.

### 4. Auto-organised "memories" / recap pages
Monthly recaps from the private Today view: most-saved topics, themes from likes, embedded voice notes. Uses the existing themes analysis on the server.
**Effort:** medium — ~1–2 weeks on top of the existing themes pipeline.
**Local-first:** partial — compilation happens server-side on the (opt-in) synced data.

### 5. Pro badge / Web Store distribution (extra, not a headline feature)
Signed Chrome Web Store build for smoother installs and updates.
**Effort:** low — ~3–5 days (one-time Web Store signing).
**Local-first:** yes.

## Options for the launch line-up (max 3)

- **Option A — "Pro = memory" (recommended):** ship 1 + 2. Voice without limits and searchable collections are the clear "why pay" for the core promise: your likes, explained and organised.
- **Option B — "Pro = peace of mind":** ship 3, with 5 as an extra. Cheapest and fastest, but backups alone rarely justify $5/mo.
- **Option C — full bundle:** 1 + 2 + 3 at launch, 4 and 5 as later extras. Most sellable, but ~4–6 weeks before Pro can launch.

**Recommendation: Option A**, with 3 following in the next release; it matches the founder-tier story and every Pro feature can stay local-first.
