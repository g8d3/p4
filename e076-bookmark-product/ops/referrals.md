# BookmarkVault referrals — full rules (v0.1.0)

Goal: pay referrers 20% of referred subscriptions as account credit,
fraud-resistant, with zero agent-held secrets. Cash payouts are
human-gated (see `ops/needs.json`: `PAYOUT_ADDRESS`).

## 1. Link + attribution flow

1. Referrer gets a per-user `CODE` from `GET /v1/referrals/me`.
   Codes are case-insensitive alphanumeric (`[A-Za-z0-9]{4,16}`).
2. Share link: `PUBLIC_URL/?ref=CODE`.
3. Landing (`sites/landing/index.html`) reads `?ref=` on load and sets
   `bv_ref=CODE; Max-Age=2592000; Path=/; SameSite=Lax` (30 days).
   **First-touch wins:** an existing `bv_ref` cookie is never overwritten.
4. At checkout, the frontend reads the `bv_ref` cookie and calls
   `POST /v1/referrals/attribute` with body `{code}` before creating
   the payment session, so the purchase is linked even if the cookie
   is later cleared.
5. Self-referral is rejected: if `code` owner == buyer account,
   attribution returns `{attributed: false, reason: "self-referral"}`.

## 2. API contract (backend implements; test mode until keys wired)

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/referrals/me` | Own code, clicks, `held` / `payable` balances |
| POST | `/v1/referrals/attribute` | Body `{code}`; links buyer to referrer, sets `ref` cookie server-side as backup |

`GET /v1/referrals/me` response shape:
```json
{"code": "AB12CD", "clicks": 17, "held": 0, "payable": 0, "currency": "USD"}
```

## 3. Rewards + 30-day hold

- Reward: **20% of the referred subscription**, credited to the
  referrer's BookmarkVault account by default (discount on renewal).
- **30-day hold:** on payment, the commission enters `held`. After
  30 days with no refund/chargeback it moves to `payable`.
  A refunded payment voids its commission (moved out of `held`,
  logged with reason `refund-void`).
- Cash payout (crypto to `PAYOUT_ADDRESS`) only after the human
  confirms the payout address in `ops/cycle.html (Keys tab)`. The agent
  never holds private keys; payouts are manual until volume
  justifies automation.

## 4. Test mode (no keys yet)

Until the human wires fiat/crypto merchants via `ops/cycle.html (Keys tab)`:
webhook handlers log `unverified-test-event` and only entitle
`plan: test`. Referral commissions created from test payments stay
labeled `test` and never enter `held`/`payable`.

## 5. Abuse guards

- No bidding on BookmarkVault brand keywords with referral links.
- No spam (unsolicited bulk DMs/posts); violations void commissions.
- One account per person for earning; the agent may void commissions
  on refund/fraud patterns and must log `{code, reason, date}`.
- Payouts pause automatically while `blocked_on_human` still contains
  `crypto-wallet` (no address = credit-only mode).

## 6. QA checklist (no backend needed)

- [ ] Open landing with `?ref=TEST12` → `bv_ref` cookie set, 30-day expiry.
- [ ] Reopen with `?ref=OTHER99` → cookie still `TEST12` (first-touch).
- [ ] `POST /v1/referrals/attribute {code:"test12"}` (lowercase) → attributed.
- [ ] Self-referral attempt → `{attributed:false}`.
- [ ] Refund simulation → commission voided with `refund-void` log.

*Doc version: v0.1.0 — matches `ag-01/SPEC.md` §3.*
