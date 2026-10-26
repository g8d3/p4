# q80 review: q76 waitlist worker (eb2722a) + q75 agents form (cd7cb4f)

Reviewer: Mango. Read-only on Rayo's branches (scratch worktrees in /tmp, since removed). No commits, no deploy, no account. Times Bogotá (UTC-5).

## 1) Worker e2e rerun — PASS
`node test/worker_e2e.mjs` in a scratch checkout of `eb2722a`, unmodified:
`PASS worker e2e: validate paid/unknown/tampered + dodo issued/duplicate/401 + nowpayments issued/duplicate/ignored/401 + waitlist cors/valid/duplicate/invalid/honeypot/origin/rate-limit`

## 2) Site gate + test_pagina_ventas, both builds — PASS
Built in a scratch checkout of `cd7cb4f`, unmodified (`sitio_unico.py` + `directorio/motor.py build --no-review`, local `estado/` copy):
- Default build (no `AGENTS_WAITLIST_URL`): `check_sales_rules.py` **17/17 pass**; `test_pagina_ventas.py` **ok**.
- Connected build (`AGENTS_WAITLIST_URL=http://127.0.0.1:8789/waitlist`): **17/17 pass**; **ok**. Form `action` points at the worker; connected FAQ copy (`a2_live`, storage disclosure) renders; the only `TODO-NOVA` left in `/agents/` is an HTML comment (gate `NO_VISIBLE_TODO` passes).

## 3) /waitlist code checks (worker.js, read not run)
- Email never logged: **PASS** — no `console.*`/`print` anywhere in worker.js.
- Email never echoed: **PASS** — all responses are `{ok:true}` / `{ok:false,error}` with no address; e2e asserts the response body excludes it.
- **ATTENTION — email IS stored in plaintext in KV** (`{email, lang, ts}` at `w:<sha256>`). The "never stored in plain text" check does not hold as literally stated. This is required for the feature (a hashed address cannot be contacted), the key itself is a hash, and the connected FAQ copy discloses the storage — but it is a fact Coco should know before any real deploy. No code fix proposed (hashing would break contactability); if policy needs it, say so and the fix is a crypto-shredding key or field-level encryption.
- Duplicates keep the first ts: **PASS** (write guarded by `if (!existing)`; e2e resubmits uppercased and asserts unchanged ts).
- Honeypot stores nothing: **PASS with a nuance** — no record is written for bots (e2e asserts KV null). Nuance: the per-IP rate-limit counter increments *before* the honeypot/validation checks, so bot and malformed requests still burn quota. Harmless in practice (quota is per IP, so a bot only throttles itself); no fix needed.
- Origin allowlist: **PASS** (`https://evil.example` → 403; preflight 204 echoes only the allowed origin; default `https://echolike.app`).
- Rate limit: **PASS** (5 then 429 with `rate_limited`; also observed live: a 6th signup from the test IP got 429 and the form showed the error message).

## 4) Phone form test, EN + ES — PASS
Headless Chrome 390×844 against the connected local build + local worker (dev port 8789, `WAITLIST_ORIGIN=http://127.0.0.1:8010`, no branch edits):
- EN: typed address → submitted → `Thanks — you're on the waitlist.` Buttons thumb-sized, no overflow (screenshots below).
- ES: same flow → `Gracias — ya estás en la lista de espera.`
- KV confirms both: `{"email":"q80review-en@example.com","lang":"en","ts":"2026-10-26T03:34:02.636Z"}`, ES record with `lang:"es"`.
- Screenshots: `/tmp/opencode/q80_agents_en_390.png`, `/tmp/opencode/q80_agents_es_390.png` (scratch copies; ask if you want them attached).

## Verdict
**PASS with one disclosed fact (plaintext email in KV, by design).** No blocking bug found, no fix required. Suggested follow-ups for Coco, none urgent: (a) confirm the plaintext-email posture before real deploy; (b) when the endpoint goes real, `WAITLIST_ORIGIN` must be the production origin and the Privacy Policy must name the store.

## Update 2026-10-26 (q85, Juan's decision)
Plaintext email storage is gone on branch `waitlist-encrypted-emails` (@ 505271d): KV now holds `{enc, lang, ts}` where `enc` is AES-GCM (random IV, key = `WAITLIST_EMAIL_KEY` Worker secret, never in the repo); missing/invalid key → 503 and nothing stored. E2E proves no plaintext in KV, decrypt round-trips, and the 503 path stores nothing. Privacy EN/ES updated. Still local, unpushed, undeployed.
