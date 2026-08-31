import type { PaymentProvider, PaymentRequest, PaymentResult } from "./types";

/**
 * Multichain crypto adapter - Helio is the best MoR-like for crypto (multichain out of box)
 * Alternatives: DePay, NOWPayments, Coinbase Commerce (EVM only)
 * Env: HELIO_API_KEY, HELIO_WEBHOOK_SECRET
 *
 * Helio supports: Solana, EVM (Base, ETH, Arbitrum, Polygon), etc. Single checkout URL.
 * Docs: https://docs.hel.io
 */
export class HelioMultichainProvider implements PaymentProvider {
  name = "helio";
  rail = "crypto" as const;

  async createCheckout(req: PaymentRequest) {
    // TODO: POST https://api.hel.io/v1/paylink with amount, chains: ["SOL","BASE","ETH"]
    // For now mock - UI can select chain, we generate a paylink
    const providerRef = `helio_mock_${Date.now()}`;
    return {
      checkoutUrl: `/api/pay/mock-checkout?ref=${providerRef}&amount=${req.amountUsd}&rail=crypto`,
      providerRef,
    };
  }

  async handleWebhook(rawBody: Buffer, headers: Record<string, string>): Promise<PaymentResult> {
    // verify helio signature
    return { status: "confirmed", providerRef: headers["x-helio-id"] || "mock", confirmedAt: new Date().toISOString() };
  }

  async verifyOnChain(txHash: string, expectedUsd: number): Promise<PaymentResult> {
    // TODO: verify via Helius (Solana) + viem (EVM) that tx sent USDC to our address
    return { status: "confirmed", providerRef: txHash, confirmedAt: new Date().toISOString() };
  }
}

// Generic multichain fallback - any provider that gives us a paylink + webhook
export class GenericCryptoProvider implements PaymentProvider {
  constructor(public name: string = "generic_crypto") {}
  rail = "crypto" as const;

  async createCheckout(req: PaymentRequest) {
    return {
      checkoutUrl: `/api/pay/mock-checkout?ref=${this.name}_${Date.now()}&amount=${req.amountUsd}`,
      providerRef: `${this.name}_${Date.now()}`,
    };
  }
  async handleWebhook(rawBody: Buffer, headers: Record<string, string>): Promise<PaymentResult> {
    return { status: "confirmed", providerRef: "mock", confirmedAt: new Date().toISOString() };
  }
}
