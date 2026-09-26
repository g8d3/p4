# ag-01 — BookmarkVault builder spec

Local-first X-bookmark backup: MV3 extension + backend + API/MCP. No secrets in repo.

## 1. MV3 extension architecture

- `manifest.json` (MV3): `host_permissions` for `x.com`, `twitter.com`; `storage`, `alarms`, `sidePanel`.
- `background.js` (service worker): scheduler (alarms), queue, upload retry, auth token in `chrome.storage.local`.
- `loader.js` (runs on x.com/i/bookmarks): dual capture, never auto-clicks without user present.
- `sidepanel/` : search, labels, sync status, export buttons.

### Dual capture: XHR + DOM

- **XHR hook (primary):** intercept bookmark-timeline XHR/fetch responses in page context, parse tweet JSON, dedupe by tweet id, forward to background queue.
- **DOM scrape (fallback):** parse `article[data-testid=tweet]` nodes for id/text/author/time; used when XHR shape changes or responses are truncated.
- Merge rule: XHR wins on conflict; DOM fills gaps. Store `source: xhr|dom` per record.

### Human-piggyback rules (hard)

1. Extension only reads while the user browses bookmarks normally. No background auto-scroll, no hidden tabs, no credential use.
2. Pagination = user scrolls; extension observes. Max 1 timeline request per user gesture chain.
3. Backoff on 429/captcha: pause 10 min, show "X asked us to slow down" notice. Never bypass login walls or rate limits.
4. All captures are local-first (IndexedDB); upload only with valid auth token, batched, user-visible status.

### Resilience agent + risk scoring

- `resilience.js` runs pre-sync: scores each sync plan 0–100.
- Signals: error rate last 24h (+30 if 429 seen), XHR schema drift (+25 if unknown fields), DOM/XHR mismatch rate (+20 if >10%), queue age (+15 if oldest >24h), consecutive failures (+10 each, cap 30).
- Action: score <40 → sync normally; 40–70 → slow mode (half batch, 2x interval, notify user); >70 → pause + surface reason in sidepanel. Score logged with every upload batch.

## 2. Backend endpoints (stub-first, test mode)

Base: `API_BASE` from extension settings. Auth: Bearer user token.

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/bookmarks/import` | Batch upsert `{tweets:[{id,text,author,created_at,source}]}`; returns `{accepted, dupes}` |
| GET | `/v1/bookmarks?q=&label=` | Full-text search + label filter |
| GET/POST | `/v1/labels` | List / create labels |
| POST/DELETE | `/v1/bookmarks/:id/labels` | Attach / detach label |
| POST | `/v1/webhooks/bookmarks` | User-configured outbound webhook on new import (URL stored per user) |
| GET | `/v1/referrals/me` | Own code, clicks, held/paid balance |
| POST | `/v1/referrals/attribute` | Body `{code}`; sets `ref` cookie (see ops/referrals.md) |
| POST | `/v1/billing/fiat-webhook` | Fiat merchant test-mode handler (signature check, `checkout.completed` → entitle) |
| POST | `/v1/billing/crypto-webhook` | Crypto merchant test-mode handler (IPN/HMAC check, `confirmed` → entitle) |

Webhook handlers run in **test mode** until human wires production keys via `ops/cycle.html (Keys tab)`: verify signature if secret present, else log `unverified-test-event` and never entitle paid plans — only `plan: test`.

## 3. Referrals (summary; full rules in ops/referrals.md)

- Link: `PUBLIC_URL/?ref=CODE`. Landing stores `ref` cookie (30 days, first-touch wins).
- Checkout sends cookie value to `/v1/referrals/attribute`.
- Payouts held 30 days (refund window), then payable to referrer balance.

## 4. Build order (keep small)

1. Extension stub: manifest + content dual-capture + sidepanel search over IndexedDB.
2. Backend stub: endpoints above as in-memory handlers + test-mode webhook logs.
3. Landing + `sites/landing/dev.html` + `ops/referrals.md`.
4. Wire production keys only via human gate (`ops/needs.json`).
