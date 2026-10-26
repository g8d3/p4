# EchoLike 2.7.0 — Chrome Web Store + Edge Add-ons listing draft

Status: **draft only. Nothing submitted, uploaded, pushed or published.**
Verified 2026-10-25 (Bogotá) against `extension_echolike/manifest.json`, shipped JS, `_locales/en|es`, `dist-chrome-2.7.0/echolike-2.7.0-chrome.zip`, and the live pages `https://echolike.app/`, `/privacy/`, `/es/privacy/` (both 200).

## License — q52 (2026-10-25 ~20:00 Bogotá). Nova/Coco decide; nothing picked in code, no LICENSE file added.

What the repo and site claim today (all read live, nothing invented):
- No `LICENSE` file anywhere: repo root, `e092-echolike/`, `echolike-extension/` — none. Manifests carry no license field (MV3 has none).
- Live site is clean: homepage + FAQ say "The extension is free." No MIT / open-source claim anywhere on echolike.app (checked Oct 25).
- Contradiction in source: `sitio_unico.py` still holds 3 unshipped MIT strings — `ext_lead` EN "Free and open source (MIT)" (line ~335), ES "Gratis y de código abierto (MIT)" (~354), and the table row "The extension, MIT licensed, no build step." (~472). None is in the built/deployed HTML today. Whichever option Nova picks, these strings must be aligned before they ship.
- AMO blocks on this: the submission flow requires "License: select the appropriate license for your add-on" ([submitting-an-add-on](https://extensionworkshop.com/documentation/publish/submitting-an-add-on/)). No selection = no listing.

Options (max 3, tradeoffs honest):
1. **All Rights Reserved (proprietary, closed).** Fits a $60/yr paid Pro: no one may copy/redistribute; keeps the code private while selling licenses. AMO needs: select "All Rights Reserved" (or Custom with one sentence) at submission — nothing else, no file required. Cost: must delete/fix the 3 MIT strings in `sitio_unico.py` so the site never promises open source; "free extension, paid Pro" stays true.
2. **MIT (permissive open source).** Anyone may use/fork/sell copies; Nova still sells Pro (hosting, sync, brand), but cannot stop clones — including a free clone of the free tier. AMO needs: select MIT/X11 at submission + add a real `LICENSE` (MIT text, copyright holder = Nova) at repo root and in the zip. Cost: one file + keeping the 3 `sitio_unico.py` strings (they become true).
3. **Source-available, non-compete (e.g. PolyForm Noncommercial or custom "view but don't resell").** Middle ground: code readable, competitors may not sell it. AMO needs: Custom license with the full text pasted at submission + `LICENSE` file in repo/zip. Costs: AMO reviewers read custom licenses more slowly (slower review); Nova must actually enforce it himself (a custom license is only as strong as his willingness to send a takedown); PolyForm variants forbid commercial use by others, which also blocks well-meaning redistributors (Linux distros, translators).

Recommendation: none from Mango — Nova/Coco decide. If the goal is Pro revenue with minimum friction, option 1 is the smallest step (no new file, AMO unblocked in one dropdown, only the 3 strings to clean). If Nova wants community trust/forks, option 2 (one LICENSE file). Say the word and the follow-up is mechanical.

## Store submission check — 2026-10-25 19:30, updated 19:37 after rebuild into new folders (Bogotá)

Checked against the real zips and official docs: [Chrome images](https://developer.chrome.com/docs/webstore/images), [Chrome listing fields](https://developer.chrome.com/docs/webstore/cws-dashboard-listing), [Chrome privacy fields](https://developer.chrome.com/docs/webstore/cws-dashboard-privacy), [Edge publish requirements](https://learn.microsoft.com/en-us/microsoft-edge/extensions/publish/publish-extension), [AMO submission](https://extensionworkshop.com/documentation/publish/submitting-an-add-on/).

### Chrome Web Store — `dist-chrome-2.7.0-storeblockers/echolike-2.7.0-chrome.zip`

| Requirement | Status | Evidence |
|---|---|---|
| MV3 manifest, name, version, 128 icon | **PASS** | `manifest_version 3`, `2.7.0`, icons 16/32/48/128 exactly |
| Short description ≤132 chars (manifest `__MSG_extDescription__`) | **PASS** | 126 EN / 132 ES in the rebuilt zip (`store-blockers`) |
| Detailed description present | **PASS** | EN 1,546 / ES 1,666 chars in this file |
| ≥1 screenshot, 1280×800 or 640×400, max 5 | **PASS** | 5 × 1280×800: popup, options, note, voice, sync |
| 128×128 store icon | **PASS** | `icons/icon128.png` = 128×128 in package |
| Privacy policy URL reachable | **PASS** | https://echolike.app/privacy/ and `/es/privacy/` → 200 |
| Permission justifications | **PASS** | all manifest permissions justified below |
| Only needed permissions | **PASS** | `clipboardWrite` absent; storage/alarms/scripting/tabs/unlimitedStorage only |
| No remote code | **PASS** | all JS bundled, no eval/Function/innerHTML |
| `update_url`/`key` stripped for store | **PASS** | both absent in this zip |
| Package built from current source | **PASS** | rebuilt 19:37 from `store-blockers` `77b9adb`; 14 files, sha256 `752ff2ed…f22849e` |

### Microsoft Edge Add-ons — `dist-edge-2.7.0-storeblockers/echolike-2.7.0-edge.zip`

| Requirement | Status | Evidence |
|---|---|---|
| Manifest, name, version, icons | **PASS** | MV3, `2.7.0`, 16/32/48/128 exact |
| Description 250–10,000 chars | **PASS** | same 1,546 EN / 1,666 ES copy |
| Short description from manifest | **PASS** | 126 EN / 132 ES in the rebuilt zip |
| 1–6 screenshots, 640×480 or 1280×800 | **PASS** | same 5 × 1280×800 |
| Extension logo 300×300 (min 128) | **PASS** | `reportes/chrome_store/assets/logo_300x300.png` = 300×300 |
| Privacy policy URL reachable | **PASS** | 200 (EN + ES) |
| Permission justifications | **PASS** | all permissions justified below |
| Only needed permissions | **PASS** | `clipboardWrite` absent in the rebuilt zip |
| No remote code | **PASS** | bundled JS only |
| Package built from current source | **PASS** | rebuilt 19:37 from `store-blockers` `77b9adb`; byte-identical to the Chrome zip (`752ff2ed…`) |

### Firefox AMO — `dist-amo-2.7.0/echolike-2.7.0-amo.zip`

| Requirement | Status | Evidence |
|---|---|---|
| Gecko block + id + min version + data-collection declaration | **PASS** | `echolike@nova-radar`, `strict_min_version 140.0`. 2.7.0 zip: required `none`, optional `websiteContent`. **When q63 ships: required `authenticationInfo`** (license key, sent only on Save), optional `websiteContent`; rebuild the AMO zip before submission. |
| MV3 background for Firefox | **PASS** | `background.scripts` present; `service_worker` ignored (known warning) |
| AMO lint | **PASS** | 0 errors / 0 notices / 2 known warnings |
| Summary ≤250 chars | **PASS** | 139 chars (`listing-amo-en.md`) |
| Description present | **PASS** | full description in `listing-amo-en.md`; ES copy in this file |
| Icons 16/32/48/128 | **PASS** | exact sizes in zip |
| Screenshots (same 1280×800 set usable) | **PASS** | 5 × 1280×800 available |
| Privacy policy URL reachable | **PASS** | 200 (EN + ES) |
| License choice / LICENSE file | **MISSING** | no `LICENSE` in repo/package; AMO requires a license selection (Nova decision) |
| `update_url` stripped | **PASS** | absent in AMO zip; public `key` retained, not a secret |
| No remote code / tests not shipped | **PASS** | 14 runtime files, no `tests/` |
| Real install runtime sign-off | **MISSING** | only temporary-install smoke on Firefox 158; permanent/AMO review or unbranded build still pending |

**Bottom line:** the upload candidates are the new `*-storeblockers` folders: Chrome and Edge now pass the package-level checklist (126/132 short description, no `clipboardWrite`, 14 runtime files, icons, 5×1280×800 shots, privacy URL 200). Firefox is submission-ready except the license. No upload/submit/push was done. **q63 note:** any build that includes Pro needs a rebuilt zip, the optional `echolike.app` host permission, and **Authentication information** declared in Chrome/Edge plus `authenticationInfo` in the Firefox declaration — see the q63 delta under the Chrome pack.

**Old-package note:** the previous follow-up had already overwritten the old zips; for this pass the stale copies (139/140, `clipboardWrite`, sha256 `992531f9…5361ac8e`) were reconstructed from `main`. The stale Edge copy was moved out of the Firefox folder to `dist-edge-2.7.0/echolike-2.7.0-edge.zip` (created 19:34); `dist-amo-2.7.0/` holds only the AMO zip. The stale Chrome baseline stays at `dist-chrome-2.7.0/echolike-2.7.0-chrome.zip`. They are for comparison, not byte-for-byte the original 17:17/16:37 files. Upload only from the `*-storeblockers` paths.


## Shared metadata (both stores)

| Field | Value |
|---|---|
| Extension name | **EchoLike** (`_locales/*/messages.json` → `extName`) |
| Version | 2.7.0 |
| Category | **Productivity** (Chrome: Productivity; Edge: Productivity) |
| Languages | English (default), Spanish (`default_locale: en`, `_locales/en`, `_locales/es`) |
| Homepage | https://echolike.app/ |
| Support | hello@echolike.app (also the contact shown in the extension and on the site) |
| Privacy policy | https://echolike.app/privacy/ (ES: https://echolike.app/es/privacy/) |
| Price | Free core. Pro add-on ($5/mo billed yearly = $60/yr, or $39 founder for the first 100) once the q63 build ships; the 2.7.0 upload zip predates Pro. |

## Short description (store field; Edge reads it from the manifest)

Chrome Web Store field max 132 chars; Edge's short description is the manifest `description`, so this must also replace `extDescription` (both locales) before submitting.

EN (126):
> Save X likes and bookmarks with optional voice or written notes, in your browser. Encrypted sync is opt-in and off by default.

ES (132):
> Guarda tus likes y bookmarks de X, con nota de voz o escrita opcional, en tu navegador. El sync cifrado es opcional y viene apagado.

**Blocker:** current `extDescription` is 139 chars EN and 140 ES, over the 132-char manifest/store limit. Ship the lines above (code change, not done here).

## Long description — EN

EchoLike keeps the posts you like or bookmark on X, with the context you add, in your own browser.

How it works
- Like or bookmark a post on x.com as you already do. EchoLike records it.
- Add a written note (up to 4,000 characters) or a voice note (up to 60 seconds). The microphone is used only while you record, and the browser asks first.
- Press **B** to bookmark a post from the keyboard — X has no built-in shortcut for that.
- Open the popup to see today's count and your latest events, and the options page to export or import everything as JSON.

Local-first by default
Everything is stored in this browser's extension storage. With sync off, the extension makes no network requests of its own: no account, no analytics, no ads, no tracking across sites. Uninstalling removes the local data.

Optional encrypted sync
If you turn it on (or pair from the EchoLike private page), each item is encrypted in your browser with AES-256-GCM before it leaves, published to a secret topic on ntfy.sh, and acknowledged by your paired EchoLike inbox. The relay only sees ciphertext plus the network metadata any request carries. If delivery fails, items wait in a local queue and retry.

With a paired inbox, saved posts and notes can be grouped by theme and voice notes can be transcribed there. That part is optional and only runs when you enable sync.

Works in Chrome, Edge and other Chromium browsers on desktop. Acts only on x.com / twitter.com, only when you like, bookmark or add a note — it does not read DMs, your history or other sites.

## Long description — ES

EchoLike guarda en tu propio navegador los posts a los que das like o guardas en X, junto con el contexto que añadas.

Cómo funciona
- Da like o guarda un post en x.com como ya lo haces. EchoLike lo registra.
- Añade una nota escrita (hasta 4.000 caracteres) o de voz (hasta 60 segundos). El micrófono solo se usa mientras grabas y el navegador pide permiso antes.
- Pulsa **B** para guardar un post con el teclado: X no tiene atajo propio para eso.
- Abre el popup para ver el contador de hoy y los últimos eventos, y la página de opciones para exportar o importar todo en JSON.

Local primero, por defecto
Todo se guarda en el almacenamiento de la extensión en este navegador. Con el sync apagado, la extensión no hace ninguna petición de red propia: sin cuenta, sin analítica, sin anuncios y sin rastreo entre sitios. Al desinstalarla se borran los datos locales.

Sync cifrado opcional
Si lo activas (o emparejas desde la página privada de EchoLike), cada elemento se cifra en tu navegador con AES-256-GCM antes de salir, se publica en un tema secreto de ntfy.sh y tu inbox de EchoLike lo confirma. El relay solo ve texto cifrado y los metadatos de red que lleva cualquier petición. Si falla la entrega, los elementos esperan en una cola local y se reintentan.

Con un inbox emparejado, los posts y notas guardados se pueden agrupar por tema y las notas de voz se pueden transcribir allí. Esa parte es opcional y solo funciona si activas el sync.

Funciona en Chrome, Edge y otros navegadores Chromium de escritorio. Solo actúa en x.com / twitter.com, y solo cuando das like, guardas o añades una nota: no lee tus mensajes directos, tu historial ni otros sitios.

## Privacy answers (must match the code)

### Single purpose
Save the posts a user likes or bookmarks on x.com, with optional written or voice notes, in the user's own browser — with optional, opt-in, end-to-end encrypted sync to that user's EchoLike inbox.

### What leaves the device
- **Sync off (default): nothing.** All alarms return early unless sync is on (`background.js`: `syncOn()` check); `fetch` exists only inside `publicar()` and `acuses()`, which are reachable only with sync on. Storage, export/import and the popup are local.
- **Sync on (user choice):** the like/bookmark/note/voice event, AES-256-GCM encrypted, to `https://ntfy.sh/<secret topic>`; an encrypted delivery-ack poll; an encrypted heartbeat every 30 minutes. ntfy.sh sees ciphertext plus IP, time and size.
- **Pairing:** `externally_connectable` accepts a `{tipo:"emparejar"}` message only from `https://echolike.app/*` (the private page's Connect button). No other origin is accepted.
- **Pro license key (only when the user saves one):** the key is authentication information, POSTed to `https://echolike.app/licenses/validate` from the Options page; nothing else is sent and no site data is read. The host permission is optional and requested in the Save-key click (q63 follow-up).
- **Not sent anywhere:** browsing history, DMs, cookies, passwords, other sites, location, contacts.

### Data disclosure checkboxes (Chrome privacy tab and Edge data usage)
| Data type | Tick? | Why (from code) |
|---|---|---|
| Website content | ✓ | The saved post's visible text, author handle, URL and time, plus the note/audio the user attaches to it. |
| User activity | ✓ | The like / unlike / bookmark / un-bookmark / note action on x.com and its timestamp. |
| Personally identifiable information | — | No name, email, phone, address or account identity is collected. Handles are public post metadata, not user PII. |
| Authentication information | ✓ (Pro only) | The **license key the user pastes** in Options, sent to `https://echolike.app/licenses/validate` only when they click **Save key** (q63, local branch `q63-pro-license-e2e`). It is not read from any website and no other auth data (passwords, cookies, tokens) is touched. |
| Health, financial/payment, personal communications, location, web history | — | No code path reads or stores these. |
| Certifications | ✓ all | Not sold; not used for unrelated purposes; not used for creditworthiness/lending. |

Edge Partner Center uses the same categories; mirror these ticks and the policy URL.

### Permission justifications
- `storage` — stores saved posts/notes, settings, the encrypted-delivery queue, the last 20 events, today's counters and the user's own pairing code. Local only.
- `unlimitedStorage` — keeps the local archive (text and voice notes) without a quota prompt. No remote copy unless the user enables sync.
- `alarms` — retries the local delivery queue and sends the encrypted heartbeat; both only when sync is on.
- `scripting` — after install/update, injects the extension's own `content.js`/`content.css` into already-open X tabs. No remote code.
- `tabs` — used with `scripting` to find those already-open X tabs by URL; not browsing history.
- `clipboardWrite` — copies the user's own pairing code in the popup. Note: the shipped code uses `navigator.clipboard.writeText`, which does not require this permission; **drop it from the manifest before submission** to avoid an unnecessary permission warning.
- Host `https://x.com/*`, `https://twitter.com/*`, `https://mobile.x.com/*`, `https://mobile.twitter.com/*` — the content script runs only there to detect the user's Like/Bookmark clicks and show the note/voice UI.
- Host `https://ntfy.sh/*` — publishes/reads the encrypted sync messages, only with sync on.
- Microphone — not a manifest permission: the x.com page asks at record time, inside the user's click.

### Remote code
**No.** All JavaScript ships in the package. No `eval`, `new Function`, or `innerHTML` in shipped code (grep of `extension_echolike/*.js|*.html`); DOM is built with `createElement`/`textContent`.

### Reviewer test notes (suggested)
1. Install, open the popup: show "saved in this browser" copy and no account prompt.
2. Like a post on x.com; show the toast and the local count. Do not enable sync to prove no network (DevTools Network stays empty).
3. Add a written note (hold the heart) and a voice note (🎙), show them in the popup's local count/options export.
4. Optional: enable sync only if a test inbox code can be provided; otherwise state that sync is optional and untested in review.

## Pre-submit blockers (code/policy work, out of scope here)

1. **Privacy policy is stale and contradicts 2.7.** Live `/privacy/` (Last updated Oct 17) says every event is encrypted and sent, a heartbeat every 30 minutes, and speech-to-text "providers". Code says: sync off = no traffic; heartbeat only with sync; STT is local `faster-whisper` on the mini PC. Fix before submitting (both stores compare the policy with behavior).
2. **Manifest short description is 139/140 chars** (limit 132). Use the lines above in `_locales/en|es`.
3. **`clipboardWrite` is unnecessary** for the shipped code; remove it.
4. Store zip: `update_url` and `key` are already stripped in `dist-chrome-2.7.0/echolike-2.7.0-chrome.zip` — keep using that zip, not the repo manifest (which keeps them for self-hosted CRX updates).

## Screenshots needed (3–5; 1280×800 works for both stores)

Chrome: at least 1, max 5, 1280×800 **or** 640×400. Edge: max 6, 640×480 **or** 1280×800. Use **1280×800 PNG, full-bleed, square corners** for every shot so one set serves both stores.

| # | Shot | Caption | Status |
|---|---|---|---|
| 1 | Popup, sync off: privacy line, local count, Today, latest events, "Sync off by default" | "Saved in your browser. Sync is optional." | exists: `dist-chrome-2.7.0/shot-popup-1280x800.png` (recheck content, no real handles) |
| 2 | x.com post with the note box open and the "saved in this browser" toast, heart/✎/🎙 visible | "Like or bookmark, add a note in one gesture." | exists: `dist-chrome-2.7.0/shot-note-1280x800.png` (1280x800, example account) |
| 3 | Voice note controls/recording state, next to a written note | "Voice or written notes, stored locally." | exists: `dist-chrome-2.7.0/shot-voice-1280x800.png` (1280x800) |
| 4 | Options page: privacy explanation + Export / Import buttons | "Your data, exportable as JSON." | exists: `dist-chrome-2.7.0/shot-options-1280x800.png` (recheck) |
| 5 | Popup with sync on and "✓ Connected", plus a queued/sent row — test inbox and sample posts only | "Optional encrypted sync to your paired inbox." | exists: `dist-chrome-2.7.0/shot-sync-1280x800.png` (1280x800, test data only) |

Also needed: store icon `icons/icon128.png` (CWS 128×128; Edge logo 300×300, min 128×128), optional CWS small tile 440×280 (exists in `assets/promo_tile_440x280.png`), optional CWS marquee 1400×560. Edge logo 300×300: DONE - exported from `marca/avatar.png` (400×400, real source art) to `reportes/chrome_store/assets/logo_300x300.png`; size gate in `tests/check_store_metadata.py`.

## Store assets table — q57 (2026-10-25 ~20:20 Bogotá). All verified on disk, nothing uploaded.

| File | Size | Store | Status |
|---|---|---|---|
| `dist-chrome-2.7.0/shot-popup-1280x800.png` | 1280×800 | Chrome / Edge / AMO | real popup UI, demo-labeled, local-only wording |
| `dist-chrome-2.7.0/shot-options-1280x800.png` | 1280×800 | Chrome / Edge / AMO | real options UI, demo-labeled |
| `dist-chrome-2.7.0/shot-note-1280x800.png` | 1280×800 | Chrome / Edge / AMO | real note UI on example account |
| `dist-chrome-2.7.0/shot-voice-1280x800.png` | 1280×800 | Chrome / Edge / AMO | real voice UI |
| `dist-chrome-2.7.0/shot-sync-1280x800.png` | 1280×800 | Chrome / Edge / AMO | sync UI, test data only |
| `reportes/chrome_store/assets/promo_tile_440x280.png` | 440×280 | Chrome small tile (optional) | real icon + honest tagline, no fake UI |
| `~/code/p4/e092-q57/store_assets/marquee_1400x560.png` (q57 worktree, branch `q57-store-shots` `fb1469e`, not on main; source `marquee_1400x560.html`) | 1400×560 | Chrome marquee (optional) | NEW: rendered headless from real icon, honest copy only |
| `reportes/chrome_store/assets/logo_300x300.png` | 300×300 | Edge logo | real source art |
| `icons/icon128.png` | 128×128 | Chrome icon / AMO icons | in package |

Note: `shot-note-1280x720.png` / `shot-voice-1280x720.png` were byte-identical duplicates (deleted Oct 25); the folder now holds only the 5 correctly named shots.

## Edge Add-ons Partner Center — copy-paste pack (q60, 2026-10-25 ~20:50 Bogotá)
Checked against the official docs ([publish-extension](https://learn.microsoft.com/en-us/microsoft-edge/extensions/publish/publish-extension)) and the real store zip (`dist-edge-2.7.0-storeblockers`, 14 files, `clipboardWrite`/key/update_url absent). Every claim matches shipped code; nothing invented. No account created, nothing uploaded.

**Package:** upload `dist-edge-2.7.0-storeblockers/echolike-2.7.0-edge.zip`.

**Availability (suggestion; Nova decides):** Visibility Public; Markets all (default).

**Properties**
- Category: `Productivity`
- Website: `https://echolike.app`
- Support contact: `hello@echolike.app` (footer of echolike.app)
- Mature content: unchecked

**Privacy — Single Purpose Description (paste):**
> Saves the posts a user likes or bookmarks on X, with optional written or voice notes, in the user's own browser — with optional, opt-in, end-to-end encrypted sync to that user's EchoLike inbox.

**Privacy — Permission justification (one line per manifest permission; clipboardWrite is NOT in the store zip, do not add it):**
- `storage` — saved posts/notes, settings, encrypted-delivery queue, last 20 events, today counters, pairing code. Local only.
- `unlimitedStorage` — local archive without quota prompt; no remote copy unless the user enables sync.
- `alarms` — retries the local queue + 30-min encrypted heartbeat; both only with sync on (`syncOn()` gate).
- `scripting` — injects the extension's own content.js/css into already-open X tabs after install/update. No remote code.
- `tabs` — finds those already-open X tabs by URL; not browsing history.
- Host `x.com / twitter.com / mobile.x.com / mobile.twitter.com` — content script runs only there, only on the user's Like/Bookmark clicks.
- Host `ntfy.sh` — encrypted sync publish/read, only with sync on.
- Optional host `https://echolike.app/*` (q63) — POSTs only the license key to `/licenses/validate` when the user clicks **Save key**; requested at that moment, not at install, and never read from sites.

**Privacy — Are you using remote code?** No. All JS ships in the package; no eval/new Function/innerHTML.

**Privacy — Data usage (tick Website content + User activity + Authentication information; leave the rest unticked; tick all certifications):** saved post text/handle/URL/time + attached note/audio; the like/bookmark/note action + timestamp; the Pro license key (authentication information), sent only when the user saves one (q63). No PII, health, financial/payment, communications, location or history code paths exist. Certifications: not sold; no unrelated purposes; no credit/lending use.

**Privacy — Privacy Policy URL:** `https://echolike.app/privacy/` (EN; ES: `https://echolike.app/es/privacy/`).

**Store listing EN (Details page; name + short description are read-only from the manifest):**
- Extension name: `EchoLike` (manifest `__MSG_extName__`)
- Short description (manifest, 126 chars): `Save X likes and bookmarks with optional voice or written notes, in your browser. Encrypted sync is opt-in and off by default.`
- Description (1,546 chars, paste the `Long description — EN` section above verbatim; 250–10,000 required)
- Extension logo: `reportes/chrome_store/assets/logo_300x300.png`
- Small promotional tile: `reportes/chrome_store/assets/promo_tile_440x280.png`
- Large promotional tile: `~/code/p4/e092-q57/store_assets/marquee_1400x560.png` (q57 worktree, branch `q57-store-shots`, not merged to main yet)
- Screenshots: the 5 × `dist-chrome-2.7.0/shot-*-1280x800.png` (Duplicate to ES afterwards via the Duplicate option)
- Search terms (suggested, 7 terms / ≤21 words): `x likes saver, bookmark notes, voice notes, local first, encrypted sync, twitter archive, no account`
- ES: add language, paste `Long description — ES`, Duplicate logo/tiles/screenshots from EN.

**Notes for certification (paste):**
> Install, open the popup: it states data stays in this browser, no account prompt. Like a post on x.com: toast + local count appear; DevTools Network stays empty with sync off (default). Hold the heart for a written note (max 4,000 chars), tap the mic for a voice note (max 60 s, browser permission prompt). Export/Import JSON in options. Sync is optional; no test inbox is provided, so review with sync off. No test accounts, no hidden features.

## Chrome Web Store — copy-paste pack (q64, 2026-10-25 ~21:29 Bogotá)
Checked against the official docs ([listing info](https://developer.chrome.com/docs/webstore/cws-dashboard-listing), [privacy fields](https://developer.chrome.com/docs/webstore/cws-dashboard-privacy), [images](https://developer.chrome.com/docs/webstore/images)) and the real upload zip (`dist-chrome-2.7.0-storeblockers/echolike-2.7.0-chrome.zip`: 14 files, `clipboardWrite`/`key`/`update_url` absent, byte-identical to the Edge zip per the 19:37 checklist). Every claim matches shipped code; nothing invented. No account created, nothing uploaded.

**Package:** upload `dist-chrome-2.7.0-storeblockers/echolike-2.7.0-chrome.zip`. Do NOT upload the old `dist-chrome-2.7.0/echolike-2.7.0-chrome.zip` — it still contains `clipboardWrite`.

**q63 delta — rebuild before any upload that includes Pro (2026-10-26 Bogotá):** the 2.7.0 `storeblockers` zip predates q63, so it has 5 permissions / 5 hosts and no license code. A Pro build adds the optional host `https://echolike.app/*` (`optional_host_permissions`, requested only in the Save-key click, so free users see no update warning), sends the license key to `/licenses/validate` only on Save, and must be declared as **Authentication information** in the privacy tab. Re-run `tests/check_store_metadata.py` and rebuild both Chrome and Edge zips from the q63 branch before submitting; the copy below is already updated for that build.

**Distribution (suggestion; Nova decides):** Public visibility, all regions (dashboard defaults).

**Store listing tab**
- Category: `Productivity`
- Language: English (default) + Spanish (`default_locale: en`, `_locales/en|es` in the zip)
- Short description (dashboard field, max 132 chars; current EN is 126, verified in the zip): `Save X likes and bookmarks with optional voice or written notes, in your browser. Encrypted sync is opt-in and off by default.`
- Detailed description (paste the `Long description — EN` section above verbatim: 1,546 chars; ES `Long description — ES` for the Spanish listing)
- Store icon: in-package `icons/icon128.png` = 128×128 ([images doc](https://developer.chrome.com/docs/webstore/images) requires the 128×128 icon in the ZIP)
- Screenshots (required: at least 1; this pack has 5, all exactly 1280×800, all showing the actual extension UI per the images doc): `dist-chrome-2.7.0/shot-popup-1280x800.png`, `shot-options-1280x800.png`, `shot-note-1280x800.png`, `shot-voice-1280x800.png`, `shot-sync-1280x800.png`
- Small promo tile 440×280: `reportes/chrome_store/assets/promo_tile_440x280.png` (optional)
- Marquee 1400×560: `~/code/p4/e092-q57/store_assets/marquee_1400x560.png` (q57 worktree, branch `q57-store-shots`, not merged to main yet; optional)
- Website: `https://echolike.app`; support contact `hello@echolike.app`

**Privacy tab — Single purpose (paste):**
> Saves the posts a user likes or bookmarks on X, with optional written or voice notes, in the user's own browser — with optional, opt-in, end-to-end encrypted sync to that user's EchoLike inbox.

**Privacy tab — Permission justification (one line per permission in the upload zip; `clipboardWrite` is NOT in it, do not add it):**
- `storage` — saved posts/notes, settings, encrypted-delivery queue, last 20 events, today counters, pairing code. Local only.
- `unlimitedStorage` — local archive without quota prompt; no remote copy unless the user enables sync.
- `alarms` — retries the local queue + 30-min encrypted heartbeat; both only with sync on (`syncOn()` gate).
- `scripting` — injects the extension's own content.js/css into already-open X tabs after install/update. No remote code.
- `tabs` — finds those already-open X tabs by URL; not browsing history.
- Host `x.com / twitter.com / mobile.x.com / mobile.twitter.com` — content script runs only there, only on the user's Like/Bookmark clicks.
- Host `ntfy.sh` — encrypted sync publish/read, only with sync on.
- Optional host `https://echolike.app/*` (q63) — license-key validation only, sent when the user clicks **Save key**; requested at that moment, never read from sites.

**Privacy tab — Remote code:** No. All JavaScript ships in the package (MV3 forbids remote code); no eval/new Function/innerHTML in shipped code.

**Privacy tab — Data usage (tick Website content + User activity + Authentication information; leave the rest unticked; tick all certifications):** saved post text/handle/URL/time + attached note/audio; the like/bookmark/note action + timestamp; the Pro license key (authentication information), sent only on Save (q63). No PII, health, financial/payment, communications, location or history code paths exist. Certifications: not sold; no unrelated purposes; no credit/lending use. Privacy policy: `https://echolike.app/privacy/` (EN; ES: `https://echolike.app/es/privacy/`).

**Test instructions for reviewers (paste):**
> Install, open the popup: it states data stays in this browser, no account prompt. Like a post on x.com: toast + local count appear; DevTools Network stays empty with sync off (default). Hold the heart for a written note (max 4,000 chars), tap the mic for a voice note (max 60 s, browser permission prompt). Export/Import JSON in options. Sync is optional; no test inbox is provided, so review with sync off. No test accounts, no hidden features.

## What was NOT done
No account creation, no upload, no submission, no push, no publish, no code change (the three blockers above are listed, not fixed).
