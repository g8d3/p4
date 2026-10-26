# Pro FAQ — payment answers (drafts, EN+ES)
By Mango Z · 2026-10-26 02:20 Bogotá. **Draft only — nothing published.** Grounded in: `checkout_options.md` (fee/MoR research, verified pricing pages), Dodo docs (docs.dodopayments.com — License Key Management v0.14.0, Manual License Key Fulfillment guide, refunds in changelog), NEXT.md. Facts not verifiable today are marked **TODO/unknown** — never guess.

## Context for these drafts
- Plan (Nova, Oct 25): **Dodo Payments is primary** for card checkout (pays out to Colombia; 4% + 40¢, license keys included, MoR). **Lemon Squeezy is the fallback** only if Dodo KYC rejects Nova (5% + 50¢, license-key API, Colombia verified). **Crypto via NOWPayments: approved, account not set up yet — TODO.**
- The drafts below lead with Dodo; re-verify each answer if checkout ends up on the LS fallback.

## FAQ entries (EN + ES)

### 1. How do I pay for Pro? / ¿Cómo pago Pro?
**EN:** "With a credit or debit card at checkout. Payments are handled by a merchant-of-record provider (Lemon Squeezy or Dodo Payments), so sales tax is calculated and remitted for you — you never send us your card details."
**ES:** "Con tarjeta de crédito o débito en el momento del pago. Los pagos los gestiona un proveedor tipo merchant-of-record (Lemon Squeezy o Dodo Payments), que calcula y declara los impuestos por ti: nunca nos envías los datos de tu tarjeta."
_TODO: confirm crypto (NOWPayments) once researched — do not publish a crypto answer before then._

### 2. How do I get my license key / unlock Pro? / ¿Cómo recibo mi licencia?
**EN:** "Right after payment you receive a license key by email and on the order confirmation page. You enter it once in the EchoLike inbox; it validates against our license API and unlocks Pro on that browser."
**ES:** "Justo después del pago recibes una clave de licencia por correo y en la página de confirmación. La introduces una vez en tu inbox de EchoLike; se valida contra nuestra API de licencias y activa Pro en ese navegador."
_Grounded in: Dodo License Key Management + manual fulfillment guide (docs.dodopayments.com); LS ships the same via its license API (docs.lemonsqueezy.com/help/licensing). TODO: the exact key-to-extension delivery flow — decide at integration time._

### 3. What happens if I want a refund? / ¿Y si quiero un reembolso?
**EN:** "Write to hello@echolike.app within 14 days and we refund you via the same payment provider — no questions asked for the yearly plan's first year." (14-day promise is **TODO: Nova sets the real policy**; both providers support refunds — Dodo changelog documents partial refunds; LS supports them.)
**ES:** "Escribe a hello@echolike.app dentro de los 14 días y te reembolsamos por el mismo proveedor de pago, sin preguntas el primer año del plan anual." (_Ver la nota TODO arriba: la política real la define Nova._)

### 4. Is checkout secure / who processes my payment? / ¿Es seguro el pago?
**EN:** "Checkout runs on the provider's PCI-compliant page — we never see or store your card. We only receive your email, the license status and the payment confirmation."
**ES:** "El pago se realiza en la página del proveedor, conforme a PCI: nunca vemos ni guardamos tu tarjeta. Solo recibimos tu correo, el estado de la licencia y la confirmación del pago."

### 5. Do you support crypto? / ¿Aceptan cripto?
**EN/ES:** "TODO — not answered until Nova picks a crypto processor. NOWPayments is untested/unresearched; do not publish."
_Language stays EN for LS checkout (currency: USD); a Spanish checkout page depends on the provider's localization — **unknown, verify with the provider**._

## Publication checklist (before any of these go live)
1. Provider is decided (Dodo primary, LS fallback); NOWPayments account still to be set up.
2. Real refund window + policy set by Nova (replaces the TODO).
3. Crypto answer researched (NOWPayments) or dropped.
4. Each answer re-verified against the chosen provider's docs the week it publishes.

---

## Addendum by Rayo (2026-10-26, after q63 / q63-key-delivery) — additions only

_Draft only. These entries fill gaps in the draft above; they do not replace any answer there._

### Key delivery after payment / Entrega de la clave tras el pago

**EN:** Dodo's License Key entitlement issues one key per unit or seat and emails it to the address used at checkout; the key also appears on the return page as `license_key`. If we use the self-hosted license server instead, `license_server/delivery.py` emails the key through Resend from `hello@echolike.app` (`LICENSE_MAILER=resend`; off by default and mock-tested only, with no durable retry queue yet). The key is never returned in a webhook response or written to a log.

**ES:** La función de claves de licencia de Dodo emite una clave por unidad o asiento y la envía al correo usado en el pago; la clave también aparece en la página de retorno como `license_key`. Si usamos el servidor propio, `license_server/delivery.py` envía la clave con Resend desde `hello@echolike.app` (`LICENSE_MAILER=resend`; apagado por defecto y probado solo con un buzón simulado, sin cola de reintentos todavía). La clave nunca se devuelve en la respuesta del webhook ni se escribe en un log.

### NOWPayments delivery / Entrega con NOWPayments

**EN:** The NOWPayments IPN body has no buyer email, so the server cannot email that key automatically; it is issued with `delivery: "manual"`. Until the checkout maps `order_id` to the buyer's email, do not promise automatic crypto key delivery — say the key is sent after the payment is matched manually.

**ES:** El cuerpo del IPN de NOWPayments no trae el correo del comprador, así que el servidor no puede enviar esa clave automáticamente; se emite con `delivery: "manual"`. Hasta que el checkout relacione `order_id` con el correo del comprador, no prometer entrega automática de la clave en cripto: indicar que se envía tras emparejar el pago manualmente.

### Activation path / Ruta de activación

**EN:** Activate in the extension's **Options → Pro license** page: paste the key and click **Save key**. A valid, active key turns Pro on; a mistyped, tampered, refunded or unpaid key leaves the extension free (q63 E2E). The earlier "enter it once in the EchoLike inbox" wording does not match the shipped options page.

**ES:** Activa en **Opciones → Licencia Pro** de la extensión: pega la clave y pulsa **Guardar clave**. Una clave válida y activa enciende Pro; una clave mal escrita, alterada, reembolsada o no pagada deja la extensión gratis (E2E de q63). La frase anterior "la introduces una vez en tu inbox de EchoLike" no coincide con la página de opciones implementada.

**Still TODO-NOVA before publishing:** Dodo KYC/live products, NOWPayments account, key rail choice (Dodo built-in vs Resend), refund window, renewal model.

### Internal notes (not buyer copy)

- **Validation endpoint / rail:** if Dodo built-in License Keys are chosen, point `pro.js` at `https://live.dodopayments.com/licenses/validate` instead of the q63 `https://echolike.app/licenses/validate`, update the manifest host permission and the q64 Chrome/Edge/Firefox packs. Buyers only need "paste the key, Save key"; endpoint details stay out of buyer answers.
- **Delivery:** `q63-key-delivery` b8f4f3a adds `license_server/delivery.py` (Resend from hello@echolike.app, mock outbox, off by default). No real send yet; failed-send retry queue and the NOWPayments buyer-email mapping are still open.

### Open decision checklist

- [ ] **Renewal model (shared TODO-NOVA):** decide auto-renewing subscription vs one-year pass before writing the price and cancel answers; both must use the same wording.
- [ ] Dodo KYC + live products; NOWPayments account and coin list; key rail choice (Dodo built-in vs Resend); refund window; support address.

### Corrections to the draft above (additions only; Mango's text unchanged)

- **Entry 5 (crypto):** NOWPayments is **approved** by Nova; the account/setup is still pending, so it is not live yet. It is not "unresearched": q59 has the IPN handler and q63's local E2E covers a paid NOWPayments IPN. Keep the buyer answer as TODO until the account and coin list exist. / **Entrada 5 (cripto):** NOWPayments está **aprobado** por Nova; la cuenta y la configuración siguen pendientes, así que todavía no está activo. No está "sin investigar": q59 tiene el manejador de IPN y el E2E local de q63 cubre un IPN pagado de NOWPayments. La respuesta al comprador sigue en TODO hasta que existan la cuenta y la lista de monedas.
- **Entry 1 (card checkout):** Dodo Payments is **primary**; Lemon Squeezy is only the fallback if Dodo's KYC rejects Nova. Reorder the provider list before publishing. / **Entrada 1 (pago con tarjeta):** Dodo Payments es **primario**; Lemon Squeezy es solo el respaldo si Dodo rechaza el KYC de Nova. Reordenar la lista de proveedores antes de publicar.
