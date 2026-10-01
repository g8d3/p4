# SELL SHEET — Swarm Market v1 (e085)

## What you're selling
A live marketplace where anyone sells or rents agent swarms. 10 pricing
models, escrow + disputes, reviews, free trials, seller earnings desk.
One Python file, stdlib only, no database to run.

## Live demo (give the buyer this URL)
`https://vuos-hcar5000mi.tail6918b0.ts.net:8335/` (tailnet HTTPS, valid cert)
Show them: hero → open a swarm → rent it (escrow math on screen) →
My orders → Accept → Seller desk (earned +$). Then publish a swarm live.

## Money math (say this out loud)
- Platform takes **5%** of every order (`fee_bps` 500 in `needs.json`).
- 1,000 orders/mo × $20 avg = **$20,000 GMV → $1,000/mo fee revenue**.
- Checkout is **mock** today: escrow math is real, money moves when
  `STRIPE_SECRET_KEY` is set (Connect split already designed in).
- Price the sale on: working product + fee engine + 10-model pricing
  system + domain shortlist (`data/domains.md`, top pick `swarmly.cc`).

## What's live vs what's next (v2 — no mocks)
LIVE: 10 pricing models, real order flow (open→delivered→accepted/disputed→
released/refunded; accept LOCKED until seller delivers), 1 free trial/buyer/swarm
as $0 orders, 1-order-1-review with rating recompute, seller desk + inbox with
Deliver buttons, one handle sign-in for everything, domain RDAP check,
real Stripe Checkout + webhook verification (activates with STRIPE_SECRET_KEY),
Clerk Google hook (activates with CLERK_PUBLISHABLE_KEY), inference lanes doc.
First real listing: Profit-Ready Site Swarm (full package: domain, hosting+HTTPS,
Clerk auth, Stripe payments, Resend receipts, analytics, launch checklist).
NEXT (in `/api/needs`): Connect payouts, Resend receipts send, abuse limits.

## Handover checklist
1. Buyer picks domain (`swarmly.cc` recommended) → `E085_PUBLIC_URL`.
2. Buyer sets `STRIPE_SECRET_KEY` → checkout flips mock→live, no code change.
3. Buyer sets `CLERK_PUBLISHABLE_KEY` → real Google login.
4. Buyer sets `RESEND_API_KEY` → receipts + magic links.
5. Reboot line (cron paused by owner; add when resumed):
   `@reboot cd /home/vuos/code/p4/e085-swarm-marketplace && python3 server/app.py >> server.log 2>&1`
