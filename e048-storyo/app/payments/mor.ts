import type { PaymentProvider, PaymentRequest, PaymentResult } from "./types";

/**
 * Merchant of Record adapter - Dodo Payments (primary) / Whop (alt)
 * Both are MoR: they handle VAT/tax, refunds, chargebacks.
 * Env: DODO_API_KEY, DODO_WEBHOOK_SECRET or WHOP_API_KEY
 *
 * Dodo docs: https://docs.dodopayments.com
 * Whop docs: https://docs.whop.com
 */
export class DodoMorProvider implements PaymentProvider {
  name = "dodo";
  rail = "mor" as const;

  async createCheckout(req: PaymentRequest) {
    // TODO: wire to Dodo API - POST /checkouts
    // body: { product_id, customer, metadata: { promptText, parentClipId } }
    // For now returns mock URL so UI can be built without keys
    const providerRef = `dodo_mock_${Date.now()}`;
    return {
      checkoutUrl: `/api/pay/mock-checkout?ref=${providerRef}&amount=${req.amountUsd}`,
      providerRef,
    };
  }

  async handleWebhook(rawBody: Buffer, headers: Record<string, string>): Promise<PaymentResult> {
    // TODO: verify X-Dodo-Signature with DODO_WEBHOOK_SECRET
    // if event === "payment.succeeded" -> confirmed
    return { status: "confirmed", providerRef: headers["x-dodo-id"] || "mock", confirmedAt: new Date().toISOString() };
  }
}

export class WhopMorProvider implements PaymentProvider {
  name = "whop";
  rail = "mor" as const;

  async createCheckout(req: PaymentRequest) {
    const providerRef = `whop_mock_${Date.now()}`;
    return {
      checkoutUrl: `/api/pay/mock-checkout?ref=${providerRef}&amount=${req.amountUsd}`,
      providerRef,
    };
  }

  async handleWebhook(rawBody: Buffer, headers: Record<string, string>): Promise<PaymentResult> {
    return { status: "confirmed", providerRef: headers["x-whop-id"] || "mock", confirmedAt: new Date().toISOString() };
  }
}
