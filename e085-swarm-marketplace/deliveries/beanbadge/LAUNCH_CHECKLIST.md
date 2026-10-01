# BeanBadge — Launch Checklist (order ord-1790838086664)

Fictional brand. Nothing below has been bought or created — check-only.

## Domain (CHECK ONLY — bought nothing)
- [x] RDAP check-only via `GET /api/domain-check` on the marketplace (no purchase API exists there).
- [x] Top pick: **beanbadge.coffee** → `{"available": true, "note": "No RDAP record (likely free). Confirm at checkout"}`.
- [x] Backups also likely-free: `beanbadge.co`, `getbeanbadge.com`, `trybeanbadge.com` (same RDAP note).
- [ ] **Buyer action:** re-confirm at registrar, BUY `beanbadge.coffee`, point DNS to host. (~$15–30/yr)

## Payments — Stripe (env `STRIPE_SECRET_KEY`, currently UNSET)
- [x] Server `POST /api/checkout` creates a REAL subscription Checkout session when the key is set.
- [ ] **Buyer action:** create Stripe account, `stripe login`, paste secret key as env, set success/cancel URLs to the public domain, enable webhook if needed.

## Login — Clerk (env `CLERK_PUBLISHABLE_KEY`, currently UNSET)
- [x] Frontend loads real `clerk-js` + Google sign-in ONLY when the key is served. Otherwise an honest disabled notice (no mock user).
- [ ] **Buyer action:** create free Clerk app → enable Google (shared dev keys, no GCP console) → paste publishable key.

## Email — Resend (env `RESEND_API_KEY` + `FROM_EMAIL`, currently UNSET)
- [x] Server `POST /api/subscribe` sends a REAL confirmation via api.resend.com when the key is set.
- [ ] **Buyer action:** create Resend account, verify sending domain, set `FROM_EMAIL` to that domain.

## Hosting / go-live
- [x] Demo serves locally: `python3 server.py` → `http://127.0.0.1:8337/` (binds loopback only).
- [ ] **Buyer action:** deploy this folder to a host (VPS/Fly/Render), terminate HTTPS, set the 3 env keys, point `beanbadge.coffee` DNS at it.

## Pre-launch must-dos
- [ ] Real roast/fulfillment plan (this demo ships no coffee).
- [ ] Refund + pause policy page, privacy/TOS, cookie notice.
- [ ] Analytics (Plausible/in-house) + uptime check.
- [ ] Test a REAL $1 Stripe charge + refund, real login, real email before announcing.

## How to run the demo
```bash
cd deliveries/beanbadge
python3 server.py   # http://127.0.0.1:8337/
```
Optional live mode: `STRIPE_SECRET_KEY=sk_... CLERK_PUBLISHABLE_KEY=pk_... RESEND_API_KEY=re_... python3 server.py`
