# Dodo built-in License Keys vs our q56 server sketch

Decision note, 2026-10-25 20:35 Bogotá. Read-only research; no accounts, no API calls, no server changes.

## Short answer

**Use Dodo's built-in License Keys. The q56 server is not needed.** Dodo already generates, emails, validates, activates, deactivates and revokes keys, including subscription/refund lifecycle. The extension can call Dodo's public validate endpoint directly; no webhook receiver, signature code, database or key delivery path is required.

Docs:
- Feature: https://docs.dodopayments.com/features/license-keys
- Public validate endpoint: https://docs.dodopayments.com/api-reference/licenses/validate-license
- Public activate/deactivate: linked from the feature page under "Activation, Validation, Deactivation"

## Can it do the three jobs?

| Job | Dodo built-in | q56 sketch |
|---|---|---|
| Issue a key on purchase | **Yes.** Automatic fulfillment (default) generates one key per unit/seat on `payment.succeeded` / `subscription.active` | Yes, after our webhook verifier |
| Email the key to the buyer | **Yes.** Dodo emails the key on issuance/fulfillment; also appended to `return_url` as `license_key` | **No** — plaintext is hashed and discarded; this was the blocker |
| Validate a key from the extension | **Yes.** `POST https://live.dodopayments.com/licenses/validate` with `{"license_key":"..."}`; public, no API key; returns `{"valid": true/false}` | Yes, but we host and maintain it |
| Activation limits / device binding | **Yes.** Public `/licenses/activate` returns an `lki_` instance; `/licenses/deactivate` frees it; 403/404/422 responses documented | No |
| Revoke on refund/subscription end | **Yes.** `refund.succeeded` disables keys; `subscription.cancelled/expired/on_hold/paused` disable; `plan_changed` reissues; manual revoke in dashboard/API | No (would need more webhook work) |
| Ops burden | None: Dodo stores keys per customer/product, dashboard list, webhooks optional | Hosting + HTTPS + SQLite + signature verification + idempotency + delivery + revocation + duplicate-event handling |

Dodo's automatic flow is the default: create a **License Key entitlement** once (activation limit, license length, activation message), attach it to the Pro products. For subscription products choose **No expiration**; validity follows the subscription. The extension sends the key to the public validate endpoint and gates on `valid`.

## What this means for EchoLike

- **Do not deploy q56.** Keep the branch unpushed as a reference; the missing key-delivery path alone makes it unfit.
- Add the Dodo host to the extension: `https://live.dodopayments.com/*` (and test host if needed), then wire q54's `validarLicenciaServidor_REAL` to `POST /licenses/validate`.
- Set the entitlement to **automatic** fulfillment so the buyer gets the key by email and on the return URL.
- **Caveat:** validate returns only a boolean, not a product/customer id. If the same Dodo store ever sells another product with a license key, any valid key could unlock Pro. Keep the License Key entitlement only on EchoLike Pro products, or use the activation endpoint's key/instance metadata for a stricter product check.
- No webhook endpoint is needed for the basic gate; Dodo handles refunds/subscription revocation inside its own key status.

## q56 fixes requested by Coco

Not applied: strict `whsec_`/base64, the Standard Webhooks vector, 200-unprocessable, and the README key-delivery blocker are already in `q56-dodo-license` `1ef09ec`. The remaining asks (single source event, fail-closed empty product allowlist/pepper, Content-Length cap, refund/dispute revocation) are moot if we use Dodo built-in; do not spend time on them unless we later choose to run our own license rail.
