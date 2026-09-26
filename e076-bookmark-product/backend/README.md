# Backend stub (v0.1.0) — in-memory, test mode

`backend/server.py` implements every endpoint in `ag-01/SPEC.md` §2 with
zero dependencies (Python stdlib only). Data lives in RAM; restart wipes
it. Webhook receipts append to `backend/webhook-log.jsonl`.

## Run

```bash
python3 backend/server.py            # :8899
python3 backend/server.py --port 8899
```

## Point the extension at it

1. Extension sidepanel → Settings → API base: `http://127.0.0.1:8899`
2. Token: any non-empty string (stub accepts all; optional pin via
   `BV_API_TOKEN=... python3 backend/server.py`).
3. Capture bookmarks → Sync now → `POST /v1/bookmarks/import`.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | `{ok, version, mode:test}` — no auth |
| POST | `/v1/bookmarks/import` | `{tweets:[{id,text,author,created_at,source}]}` → `{accepted, dupes}`; XHR wins on conflict |
| GET | `/v1/bookmarks?q=&label=` | Search + label filter, newest first, cap 100 |
| GET/POST | `/v1/labels` | `{name}` to create |
| POST/DELETE | `/v1/bookmarks/:id/labels` | `{label}` attach / detach (DELETE also reads `?label=`) |
| POST | `/v1/webhooks/bookmarks` | `{url}` must be https (localhost allowed); import events logged per URL |
| GET/POST | `/v1/approvals[?status=]` | Propose `{kind,title,detail}` → pending; `POST /v1/approvals/:id/approve` or `/reject` decides; nothing runs on propose |
| GET | `/v1/referrals/me` | `{code, clicks, held, payable}` |
| POST | `/v1/referrals/attribute` | `{code}` → `{attributed}` + `bv_ref` cookie; self-referral rejected; no auth |
| GET | `/v1/billing/me` | `{plan, plan_detail, catalog, history}` — catalog always matches landing: Free / Monthly $7/mo / Yearly $99/yr / Lifetime $198 one-time |
| POST | `/v1/billing/fiat-webhook` | `{"type":"checkout.completed","plan":"monthly\|yearly\|lifetime"}` → that plan, only with `FIAT_WEBHOOK_SECRET` + valid `X-Webhook-Signature`; else `plan:test` |
| POST | `/v1/billing/crypto-webhook` | `{"status":"confirmed","plan":"monthly\|yearly\|lifetime"}` → that plan, only with `CRYPTO_WEBHOOK_SECRET` + valid signature; else `plan:test` |

## Plans (match landing pricing.html + terms.html)

| Plan | Price (USD) | Interval | Webhook `plan` value |
|---|---|---|---|
| Free | 0 | none | — (default before any purchase) |
| Monthly | $7/mo | month | `monthly` |
| Yearly | $99/yr | year | `yearly` |
| Lifetime | $198 one-time | once | `lifetime` |

`resolve_plan()` also accepts `price_id`/`interval` variants containing
`monthly`/`yearly`/`lifetime`, and the legacy alias `pro` (= monthly).
Missing/unknown plan defaults to `monthly`.

## Test mode rule (hard)

Without the secret env var, billing webhooks **never** entitle a paid
plan. They log `unverified-test-event` (in memory + `webhook-log.jsonl`)
and return `{plan:"test"}`. Production keys are wired only by the human
via `ops/cycle.html (Keys tab)` — never committed, never requested by the agent.

## Smoke test

```bash
B=http://127.0.0.1:8899 H="Authorization: Bearer demo"
curl -s $B/health
curl -s -X POST $B/v1/bookmarks/import -H "$H" -H 'Content-Type: application/json' \
  -d '{"tweets":[{"id":"123","text":"hello vault","author":"@x","created_at":"2026-09-25","source":"xhr"}]}'
curl -s "$B/v1/bookmarks?q=hello" -H "$H"
curl -s -X POST $B/v1/labels -H "$H" -H 'Content-Type: application/json' -d '{"name":"read-later"}'
curl -s -X POST $B/v1/bookmarks/123/labels -H "$H" -H 'Content-Type: application/json' -d '{"label":"read-later"}'
curl -s "$B/v1/bookmarks?label=read-later" -H "$H"
curl -s $B/v1/referrals/me -H "$H"
curl -s -X POST $B/v1/referrals/attribute -H 'Content-Type: application/json' -d '{"code":"FRIEND1"}'
curl -s $B/v1/billing/me -H "$H"   # {plan:free, catalog:[free,monthly,yearly,lifetime]}
curl -s -X POST $B/v1/billing/fiat-webhook -H 'Content-Type: application/json' -d '{"type":"checkout.completed","plan":"yearly"}'
curl -s -X POST $B/v1/billing/crypto-webhook -H 'Content-Type: application/json' -d '{"status":"confirmed","plan":"lifetime"}'
curl -s -X POST $B/v1/approvals -H "$H" -H 'Content-Type: application/json' -d '{"kind":"general","title":"Resume paused sync"}'
curl -s "$B/v1/approvals?status=pending" -H "$H"
curl -s -X POST $B/v1/approvals/1/approve -H "$H" -H 'Content-Type: application/json' -d '{}'
curl -s "$B/v1/approvals" -H "$H"   # id 1 shows status:approved
tail -n 5 backend/webhook-log.jsonl
```

Expected: import `{accepted:1}`, search finds it, label attach shows
`["read-later"]`, referrals `{attributed:true}`, both billing calls
return `{plan:"test"}` and log `unverified-test-event`.

*Doc version: v0.1.0.*
