# EchoLike 2.7.0 — Firefox / AMO port check + listing draft

Status: **local analysis only. Nothing submitted, signed, pushed or published.**

Update 2026-10-25 18:30 Bogotá (Rayo, q32): branch **`q32-firefox-store` (`4612a98`)** = q29 `a7ff01d` + cherry-picked `77b9adb` (6 files). Rebuilt the Firefox package **`dist-amo-2.7.0/echolike-2.7.0-amo.zip`** in the main `e092-echolike` tree (untracked; 50 KB, `web-ext lint` 0/0/2 known warnings); `check_store_metadata` PASS (126/132 chars, no clipboardWrite). A temporary WebDriver smoke test on the official Firefox 158.0.1 tarball loaded the popup (2.7.0, sync off), round-tripped messages and saw zero ntfy/echolike requests — **not** the accepted runtime test; that stays blocked. A parallel `q32-firefox-combined` (Mango Z) also exists; it carries sales-page files, so prefer `q32-firefox-store` for the clean q29+77b9adb diff.
Checked 2026-10-25 against `extension_echolike/` source, `dist-amo-2.7.0/echolike-2.7.0-amo.zip`, `dist-amo-2.7.0/lint-amo.txt`, and Mozilla docs (MDN `externally_connectable`, Extension Workshop).

## Verdict

The Firefox package is installable in principle (MV3, `browser_specific_settings.gecko`, AMO lint 0 errors / 2 warnings), but **the 2.7.0 code would not work correctly in Firefox as shipped**: popup and options messages hang, and the background answers in the Chrome style. Three smallest fixes are implemented on local branch **`q29-firefox-port` (commit `a7ff01d`, not pushed)**. None changes Chrome behavior.

I could not run Firefox in this session (the installed Firefox is the snap; `firefox --version` fails with `user.slice ... is not a cgroup for tag snap.firefox.firefox`). So this is static + Node-level verification; a real Firefox 140+ click-through is still required before AMO submission.

## Exact blockers (pre-fix line numbers on `main`)

### 1. Popup/options pick `browser` and then use Chrome callbacks
`extension_echolike/popup.js:1` and `options.js:1`:
```js
const ext = typeof browser !== "undefined" ? browser : chrome;
```
On Firefox `browser` exists, so `ext` becomes the Promise-based namespace. The very next line, `popup.js:4` / `options.js:4`, passes a callback:
```js
ext.runtime.sendMessage(m, (r) => ok(ext.runtime.lastError ? ... : r));
```
`browser.runtime.sendMessage` takes `(message, options?)` and returns a Promise; the callback is never called. Same for `ext.runtime.lastError`. Result in Firefox: popup status stuck at "—", Sync toggle/Send test do nothing, and options Export/Import never finish.

**Fix applied:** prefer Firefox's callback-compatible `chrome` namespace (the same pattern `content.js:79` already uses):
```js
const ext = (typeof chrome !== "undefined" && chrome.runtime) ? chrome : (typeof browser !== "undefined" ? browser : null);
```
Files: `popup.js`, `options.js` (1 line each).

### 2. Background answers with `sendResponse` + `return true`
`background.js:132` registers an `onMessage` listener that ends with `p.then(responder, ...); return true;` (`background.js:141`). That is the Chrome channel. Firefox resolves the sender by the listener's **returned Promise**.

**Fix applied:** when the namespace is Firefox's `browser`, return the Promise; keep the Chrome branch unchanged:
```js
if (typeof browser !== "undefined" && ext === browser) {
  return p.then((r) => r, (e) => ({ ok: false, error: String(e && e.message || e) }));
}
p.then(responder, ...); return true;
```
File: `background.js`.

### 3. "Connect this browser" cannot work on Firefox
`popup.html:13` links to `https://echolike.app/private/`, whose Connect button calls `chrome.runtime.sendMessage(extensionId, ...)` from the page. Firefox does **not** support web page → extension messaging; MDN's `externally_connectable` page states "In Firefox, neither API is supported" (Firefox bug 1319168). `externally_connectable` in the manifest is therefore inert for web pages in Firefox.

**Fix applied:** detect Firefox (`browser.runtime.getBrowserInfo`) and hide `#conectar`. The copy-code + `/par` pairing path already in the popup remains (Sync on → code box). `externally_connectable` is left in the manifest; it still permits extension-to-extension messaging and is harmless for AMO.
File: `popup.js`.

### 4. Manifest warnings (not blockers)
- `background.service_worker` is ignored in Firefox; `background.scripts` is present and used. AMO lint: `BACKGROUND_SERVICE_WORKER_IGNORED`.
- `browser_specific_settings.gecko.strict_min_version: 140.0` + `data_collection_permissions` is correct for the built-in consent API (FF 140+). The second lint warning is the Android-not-supported note; the add-on is desktop-only by design.
- `update_url` is stripped in `echolike-2.7.0-amo.zip` (verified); AMO ignores it anyway.
- `key` stays in the AMO zip (public key, pins the ID); not a secret.

## What works / needs no change
- MV3 with `background.scripts` (classic scripts), `action`, `alarms`, `scripting`, `tabs`, `storage` + `unlimitedStorage`, host permissions, `options_ui`, `default_locale` + `_locales/{en,es}`.
- `browser.permissions.request({dataCollection:["websiteContent"]})` inside the sync toggle's click (popup.js and options.js) — FF 140+.
- `content.js` already prefers `chrome` when `chrome.runtime.id` exists (`content.js:79`), which Firefox provides in content scripts, so its callback calls (`content.js:93`, `:99`, `:271`) keep working.
- `getUserMedia`/`MediaRecorder`, `navigator.clipboard.writeText` on click, `crypto.subtle`, `btoa/atob` — all standard in Firefox.
- No `eval`/`new Function`/`innerHTML` in shipped code; no remote code.

## Verification run on the branch
```
node --check popup.js options.js background.js        -> ok
node tests/test_popup.js local|sin-codigo|sin-confirmar|conectado -> 4/4 OK
node tests/test_content.js                            -> ok 6 casos
node tests/test_firefox_compat.js                     -> ok firefox: onMessage returns a Promise (browser namespace)
```
`test_firefox_compat.js` loads `background.js` with a `browser`-only stub and asserts the listener returns a Promise and resolves for `validar` and `acuses`.

Rebuilt AMO zip from `a7ff01d` (14 runtime files, `update_url` removed, 51 KB) and linted it with `npx --yes web-ext lint` (npm cache only; nothing installed globally or committed):

```
{"summary":{"errors":0,"notices":0,"warnings":2},"metadata":{"id":"echolike@nova-radar","version":"2.7.0","firefoxMinVersion":"140.0"}}
warnings: BACKGROUND_SERVICE_WORKER_IGNORED; KEY_FIREFOX_ANDROID_UNSUPPORTED_BY_MIN_VERSION
```

Same two known warnings as the earlier package, no new ones. Zip: `/tmp/echolike-2.7.0-firefox.zip` (temporary; rebuild before submission).

Not run: real Firefox, AMO signing.

## AMO listing draft

### Shared fields
- **Name:** EchoLike
- **Category:** Productivity
- **Platform:** Firefox desktop, 140+ (`strict_min_version: 140.0`; no Android key)
- **Homepage:** https://echolike.app/
- **Support:** hello@echolike.app
- **Privacy policy:** https://echolike.app/privacy/ (ES: https://echolike.app/es/privacy/)
- **License:** **blocked** — there is no `LICENSE` file in the extension package. AMO requires a license choice (e.g. "All Rights Reserved" or MIT). Nova must decide.
- **Source code:** not obfuscated; all files in the zip.

### Summary EN (max 250)
> Save your X likes and bookmarks, with optional voice or written notes, in your own browser. Optional encrypted sync to your EchoLike inbox. (139 chars)

### Summary ES
> Guarda tus likes y bookmarks de X, con nota de voz o escrita opcional, en tu propio navegador. Sync cifrado opcional a tu inbox de EchoLike. (140 chars)

### Description EN
EchoLike keeps the posts you like or bookmark on X, with the context you add, in your own browser.

- Like or bookmark a post on x.com as you already do. EchoLike records it.
- Add a written note (up to 4,000 characters) or a voice note (up to 60 seconds). The microphone is used only while you record, and Firefox asks first.
- Press B to bookmark a post from the keyboard.
- Open the popup for today's count and recent events; the options page exports/imports everything as JSON.

Local-first: everything is stored in this browser's extension storage. With sync off, the extension makes no network requests of its own — no account, no analytics, no ads, no cross-site tracking.

Optional encrypted sync: when you turn it on, each item is encrypted in your browser with AES-256-GCM, published to a secret topic on ntfy.sh, and acknowledged by your paired EchoLike inbox. The relay sees ciphertext only. Failed deliveries wait in a local queue and retry. With a paired inbox, saved posts can be grouped by theme and voice notes transcribed there.

Pairing in Firefox uses your extension code: copy it in the popup and send `/par <code>` to the EchoLike bot. (The website's one-click Connect button is Chrome-only.)

Runs on Firefox 140+ on desktop. Acts only on x.com / twitter.com, only when you like, bookmark or add a note; it does not read DMs, history or other sites.

### Description ES
EchoLike guarda en tu propio navegador los posts a los que das like o guardas en X, junto con el contexto que añadas.

- Da like o guarda un post en x.com como ya lo haces. EchoLike lo registra.
- Añade una nota escrita (hasta 4.000 caracteres) o de voz (hasta 60 segundos). El micrófono solo se usa mientras grabas y Firefox pide permiso antes.
- Pulsa B para guardar un post con el teclado.
- Abre el popup para ver el contador de hoy y los eventos recientes; la página de opciones exporta e importa todo en JSON.

Local primero: todo se guarda en el almacenamiento de la extensión en este navegador. Con el sync apagado, la extensión no hace peticiones de red propias: sin cuenta, sin analítica, sin anuncios y sin rastreo entre sitios.

Sync cifrado opcional: al activarlo, cada elemento se cifra en tu navegador con AES-256-GCM, se publica en un tema secreto de ntfy.sh y tu inbox de EchoLike lo confirma. El relay solo ve texto cifrado. Si falla la entrega, queda en una cola local y se reintenta. Con un inbox emparejado, los posts se pueden agrupar por tema y las notas de voz transcribir allí.

En Firefox el emparejamiento usa tu código: cópialo en el popup y envía `/par <código>` al bot de EchoLike. (El botón Connect de la web es solo para Chrome.)

Funciona en Firefox 140+ de escritorio. Solo actúa en x.com / twitter.com, y solo cuando das like, guardas o añades una nota; no lee mensajes directos, historial ni otros sitios.

### Data-collection answers (AMO form)
- **Manifest declaration:** `required: ["none"]`, `optional: ["websiteContent"]` — matches the code.
- **Does it collect/transmit data by default?** No. With sync off (default), zero network requests from the extension; the popup says data stays in this browser.
- **Optional transmission:** liked/bookmarked post text, author handle, URL, time, the action, typed notes and voice audio — only after the user turns sync on. Items are AES-256-GCM encrypted in the browser; the relay (ntfy.sh) sees ciphertext plus normal network metadata.
- **Consent:** turning sync on in the popup or options calls `browser.permissions.request({dataCollection:["websiteContent"]})` inside the click. Refusing leaves sync off. Web-page pairing cannot bypass this on Firefox (page→extension messaging is unsupported).
- **Not collected:** browsing history, DMs, cookies, passwords, location, contacts, analytics.
- **Retention/deletion:** local until the user uninstalls or clears extension data; encrypted relay messages expire on ntfy.sh's schedule; inbox data until the user asks hello@echolike.app.
- **Remote code:** No.

### Reviewer notes (suggested)
1. Install on Firefox 140 desktop and open the popup: local-only copy, no account, no network.
2. On x.com, like a post: toast + local count; DevTools Network shows no requests while sync is off.
3. Add a written note (hold the heart) and a voice note (🎙, mic prompt); both appear in the popup/options export.
4. Firefox pairing: enable Sync, copy the code, send `/par <code>` to the bot. The web Connect button is intentionally hidden on Firefox.
5. Sync is optional; testers can skip it if no inbox code is available.

### Screenshots
Reuse the same five 1280×800 shots planned for Chrome/Edge (`coco/store_listings.md`): popup-local (exists), X capture + note box (needed), voice note (needed), options/export (exists), optional sync-connected popup (needed, test inbox and sample posts only). AMO displays one or more; at minimum upload shot 1 with the listing.

## Pre-submission blockers — status after q32 (Rayo, 2026-10-25 18:26 Bogotá)
1. **License not chosen / no LICENSE file.** Still open (Nova decides; license stays open per q32).
2. **Stale privacy policy** — RESOLVED AT SOURCE on `q32-firefox-store`: `reportes/chrome_store/privacy_policy*.md` from `77b9adb` matches 2.7.0 (local-first default, sync-conditional heartbeat, local STT). Publishing the rebuilt site so https://echolike.app/privacy/ shows it is still pending.
3. **Rebuild — RESOLVED** on `q32-firefox-store` (`4612a98`): Firefox zip rebuilt at `dist-amo-2.7.0/echolike-2.7.0-amo.zip` (14 runtime files, `update_url` removed, 50 KB), `web-ext lint` 0 errors / 0 notices / 2 known warnings, `test_firefox_compat` PASS, `check_store_metadata` PASS. **Runtime sign-off — BLOCKED**: it needs AMO review or an unbranded Firefox build. The official-tarball temporary install was only a smoke test (popup 2.7.0 with sync off, `acuses` round-trip, no ntfy/echolike connections); it does not replace the accepted runtime test.

4. Manifest description — not an AMO blocker (250-char summary used); store descriptions now ≤132 chars on the blockers branch.

## Build artifacts (explicit)
- **Firefox/AMO build:** `~/code/p4/e092-echolike/dist-amo-2.7.0/echolike-2.7.0-amo.zip` (main tree, untracked). This is the one with the `gecko` block and `background.scripts` for Firefox.
- `reportes/chrome_store/echolike_store_v2.7.0.zip` is **not** the AMO build: that path is the Chrome/Edge store package (`service_worker` only, no `browser_specific_settings.gecko`). Do not upload it to AMO.

## Not done
No AMO account work, no signing, no upload, no push, no deploy; no paid API. No accepted runtime Firefox test — only the temporary-install smoke test below; full runtime sign-off waits for AMO review or an unbranded build.


## q32 temporary-install smoke test (not runtime sign-off), 2026-10-25 18:26 Bogotá

Setup: official Mozilla Linux tarball **Firefox 158.0.1** under `/tmp/rayo-ff`, geckodriver 0.36.0, temporary install of the rebuilt AMO zip, headless, fresh profile, telemetry/updates disabled, logging HTTP proxy at 127.0.0.1:8899. This proves the code paths in a real Gecko build; it is **not** the permanent-install/AMO runtime sign-off, which remains blocked.

- Popup: `ver = 2.7.0`, `sync` unchecked, status "✓ Saved in this browser only | Nothing sent yet".
- Background messaging from the popup page in Firefox: `{tipo:"acuses"}` → `{"ok":true,"local":true,"nuevos":0,"uids":[]}`; `{tipo:"validar",codigo:"basura"}` → `{"error":"invalid code: must be EL2|server|topic|key"}`. This confirms the Promise-return fix for `onMessage`, not just module loading.
- Network while sync stayed off: proxy log had 4 CONNECTs, all Firefox infrastructure (`archive.mozilla.org`, `content-signature-2.cdn.mozilla.net`, `firefox-settings-attachments.cdn.mozilla.net`, `firefox.settings.services.mozilla.com`); **0 to ntfy.sh, 0 to echolike.app**. Popup screenshot: `/tmp/rayo-ff/popup.png` (temporary).
- Rebuild/lint: `dist-amo-2.7.0/echolike-2.7.0-amo.zip` 50 KB; `web-ext lint` 10.8.0 → errors 0, notices 0, warnings 2 (`BACKGROUND_SERVICE_WORKER_IGNORED`, `KEY_FIREFOX_ANDROID_UNSUPPORTED_BY_MIN_VERSION`).
- Tests: `test_firefox_compat` PASS, `test_popup` 4/4, `test_content` 6 cases, `check_store_metadata` PASS (`extDescription en 126 / es 132`, no `clipboardWrite`).

Branch: `q32-firefox-store` (`4612a98`, parent `a7ff01d`; contains `77b9adb` as a cherry-pick, 6 files vs q29). Unpushed. License remains open (Nova).
