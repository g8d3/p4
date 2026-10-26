# Checkout options for EchoLike Pro — solo seller based in Colombia

## Decision note — q49 (2026-10-26 ~00:05 UTC / flipped 2026-10-26 ~00:35 UTC: Nova chose Dodo). Read this first.
Research only — no accounts, no sign-ups, no payments. Background: Pro sales are product revenue, not own-token trading (see `coco/revenue_split_2026-10-25_v2.md`).

### Option 1 — Dodo Payments (cards + stablecoins; Nova's pick, now verified)
- Fee: **4.5% + 40¢** subscriptions, 4% + 40¢ one-time ([pricing](https://dodopayments.com/pricing)). $60 → net **$56.90**; $39 → net **$37.04**.
- MoR (tax/VAT handled) + license keys included.
- Colombia: **verified** — #33 on Dodo's [accepted countries](https://docs.dodopayments.com/miscellaneous/accepted-countries-and-territories); eligibility follows the ID-issuing country (Nova has a Colombian ID).
- Stablecoin checkout built in: buyers pay in **USDC/USDP/USDG**, Nova settles in USD ([Colombia payments guide](https://dodopayments.com/payments-in/colombia)) — no separate crypto integration needed to start.
- Setup: Nova completes Dodo KYC → $60/yr subscription product + $39 one-time product → license webhook to echolike.app unlock. Site is already being built for Dodo KYC.

### Option 2 — Lemon Squeezy (cards; fallback if Dodo KYC fails)
- Fee: **5% + 50¢** ([pricing](https://www.lemonsqueezy.com/pricing)). $60 → net **$56.50**; $39 → net **$36.55**.
- MoR + built-in license keys ([licensing docs](https://docs.lemonsqueezy.com/help/licensing)). Colombia payout verified — bank + PayPal ([supported countries](https://docs.lemonsqueezy.com/help/getting-started/supported-countries)).
- Use only if Dodo rejects KYC; do not integrate both.

### Option 3 — Crypto direct (later, only if Dodo stablecoins prove insufficient)
- NOWPayments hosted: **1% service fee** ([pricing](https://nowpayments.io/pricing)) + network fee. BTCPay Server: **0% fees** ([homepage](https://btcpayserver.org/)), self-hosted. Coinbase is **out** (US + Singapore only).
- Do this when crypto is >20% of sales AND buyers ask for coins Dodo doesn't take.

### Recommendation
**Ship Dodo for cards and stablecoins now** (Nova's pick, Colombia + stablecoin checkout both verified today). **Lemon Squeezy is the fallback if Dodo KYC fails.** No second crypto integration until Dodo's stablecoin option proves insufficient.


By Mango Z · 2026-10-25 18:30 Bogotá (UTC-5). Research only — no sign-ups, no accounts, no payments.
Product to sell: $5/mo billed yearly ($60/yr) + $39 one-time founder tier (first 100 buyers).

## Fees verified today (from the vendor pricing pages, fetched live)

| Vendor | Fee (verified source) | On $60/yr | On $39 founder | On both ($99) | MoR / tax handling | License keys | Colombia payouts | Setup effort |
|---|---|---|---|---|---|---|---|---|
| Lemon Squeezy | **5% + 50¢** per transaction; no monthly fee | $3.50 → net $56.50 | $2.45 → net $36.55 | $5.95 → net $93.05 | MoR: "Lemon Squeezy is your merchant of record… global VAT + sales tax collection included" (pricing page) | License keys — **verified Oct 25**: docs.lemonsqueezy.com/help/licensing documents "Generating license keys", "License keys and subscriptions", Lemon.js and a validate/activate API | **verified Oct 25 by Coco**: docs.lemonsqueezy.com/help/getting-started/supported-countries lists Colombia (bank + PayPal payouts) | Low: product + license webhook |
| Dodo Payments | **4% + 40¢** standard (cards); subscriptions (the $60/yr plan) 4.5% + 40¢; license key generation and delivery included | $3.10 → net $56.90 (4.5% + 40¢, subscription rate) | $1.96 → net $37.04 | $5.06 → net $93.94 | MoR: pricing page lists "Merchant of record" and "Cross-border tax & compliance handled" | License keys — **verified Oct 25**: pricing page lists "License key generation and delivery to your customer: Included"; docs have License Key Management (v0.14.0) and a Manual License Key Fulfillment guide | **verified Oct 26**: Colombia is #33 on docs.dodopayments.com/miscellaneous/accepted-countries-and-territories (eligibility by ID-issuing country); stablecoin checkout USDC/USDP/USDG per dodopayments.com/payments-in/colombia | Low-medium |
| Paddle | **5% + 50¢** per checkout transaction; no monthly fees | $3.50 → net $56.50 | $2.45 → net $36.55 | $5.95 → net $93.05 | MoR: pricing page markets "Tax & compliance" handled; Paddle acts as MoR for software | Has license-key/entitlements tooling — **not verified today** (docs partially readable; no license-key page captured) | **not verified** (docs.paddle.com payouts page had no country list in static text) | Medium-high: Paddle Billing integration is heavier than LS |
| Polar | Starter **5% + 50¢**; Pro $20/mo + 3.6% + 35¢; Scale $100/mo + 3.4% + 30¢ | Starter: $3.50 → net $56.50 | Starter: $2.45 → net $36.55 | Starter: $5.95 → net $93.05 (Pro: $20/mo = $240/yr — dwarfs revenue at this stage) | MoR-style: pricing page shows "VAT 19%" line and "Your payout" on invoices | License keys — **not verified today** | **not verified** | Low-medium |
| Gumroad | **10% + $0.50** per transaction | $6.50 → net $53.50 | $4.40 → net $34.60 | $10.90 → net $88.10 | Gumroad handles tax as MoR for digital sales — **partially verified** (pricing page fetched; tax wording **not verified**) | License-key support — **not verified today** | **not verified** | Lowest: link-only selling |
| Stripe direct | **not verified** — needs a supported entity (Stripe Colombia availability and cross-entity setup could not be verified from a fetched page today) | n/a | n/a | n/a | NOT MoR: sales tax/VAT compliance falls on the seller | Via license-key library (own implementation) | Stripe itself: **unknown**; entity requirement is the blocker | Highest: entity + tax compliance + integration |

Sources actually opened today: https://www.lemonsqueezy.com/pricing · https://www.paddle.com/pricing · https://polar.sh/#pricing · https://www.gumroad.com/pricing · https://docs.paddle.com/paddle-billing/payouts (no country list in static text).

## Unknowns that matter
- **Resolved**: Lemon Squeezy pays out to Colombia (bank + PayPal, per docs.lemonsqueezy.com/help/getting-started/supported-countries, confirmed by Coco) and ships license keys with a validate/activate API (docs.lemonsqueezy.com/help/licensing).
- **Resolved Oct 26**: Dodo Payments Colombia verified (see decision note) — table above updated. No open payout questions left on the two card routes.
- Paddle / Polar / Gumroad Colombia payouts: still **not verified** (all three out of the running).

## Coco verification (2026-10-25 18:35 Bogotá; header timestamp fixed Oct 25)
- Colombia payouts on Lemon Squeezy: CONFIRMED. Colombia is on the bank-payout list (https://docs.lemonsqueezy.com/help/getting-started/supported-countries); PayPal payouts also work. Payouts twice monthly, 13-day hold; non-US bank payouts cost 1% (Stripe), PayPal 3% capped.
- License keys on Lemon Squeezy: CONFIRMED. Generated per product with license length + activation limit; public License API activate/validate/deactivate at https://api.lemonsqueezy.com/v1/licenses/* (no API key needed, 60 req/min). Extension must check store_id/product_id in meta. Docs: https://docs.lemonsqueezy.com/api/license-api
- (Superseded Oct 25 19:55 Bogotá: Nova picked Dodo; Lemon Squeezy is now the fallback.)

## Coco review (2026-10-25 18:35 Bogotá)
- Fee math checked: all correct (5%+50¢ gives net $56.50 / $36.55 / $93.05; Gumroad 10%+50¢ gives $88.10).
- Deciding unknown resolved for Lemon Squeezy: Colombia is on the bank-payout list, and PayPal payouts also work. Payouts go out twice a month, converted to COP at the mid-market rate if chosen. Source: https://docs.lemonsqueezy.com/help/getting-started/supported-countries and https://docs.lemonsqueezy.com/help/getting-started/getting-paid
- Fixes needed: the header timestamp says 2026-10-26 00:55 "Bogotá", but that is UTC (Bogotá was Oct 25 ~18:30). Option 1 says "built-in license keys" while the table marks it unverified, so keep it as unverified until the docs confirm it. "Nicaraguan-style edge cases" looks like a stray phrase. (resolved Oct 25: header fixed, license keys verified from docs.lemonsqueezy.com/help/licensing, stray phrase removed)
- Still open: LS license-key docs (https://docs.lemonsqueezy.com/help/licensing), Paddle/Polar/Gumroad Colombia payouts.

## Coco review of q49 (2026-10-25 19:55 Bogotá)
- Fee math checked: correct (LS $56.50/$36.55, Dodo $56.90/$37.04, NOWPayments $59.40/$38.61).
- Dodo Colombia is now VERIFIED: Colombia is #33 on https://docs.dodopayments.com/miscellaneous/accepted-countries-and-territories (eligibility follows the ID-issuing country; Nova has a Colombian ID). Payouts go in USD/EUR/GBP, $50 minimum, twice monthly (https://docs.dodopayments.com/miscellaneous/faq). Dodo checkout also takes stablecoins (USDC/USDP/USDG) per https://dodopayments.com/payments-in/colombia.
- Nova already chose Dodo (Oct 23) and the site is being built for Dodo KYC. So the recommendation flips: **Dodo for cards (and stablecoins), cheaper and verified.** Lemon Squeezy is the fallback if Dodo KYC is rejected. NOWPayments/BTCPay only if Dodos stablecoin option proves insufficient.- Cleanup needed: the file has three "Recommendation" sections that disagree; keep only the decision note at the top.

- Coco re-check of q49 cleanup (2026-10-25 19:58 Bogotá): approved. One decision note, fee math rechecked, sources intact; stale LS pick line marked superseded.
