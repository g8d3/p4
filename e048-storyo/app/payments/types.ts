// Payment abstraction - same queue regardless of rail
export type PaymentRail = "mor" | "crypto";
export type PaymentStatus = "pending" | "confirmed" | "failed";

export interface PaymentRequest {
  rail: PaymentRail;
  amountUsd: number;
  // what the user bought: custom prompt or branch fork
  product: "custom_prompt" | "branch_fork" | "channel_sub";
  // the prompt text they paid to inject
  promptText: string;
  // for branching: parent clip id to fork from
  parentClipId?: string;
  // metadata from provider
  providerRef?: string;
}

export interface PaymentResult {
  status: PaymentStatus;
  providerRef: string;
  confirmedAt?: string;
}

// All providers implement this - Dodo/Whop and multichain crypto are interchangeable
export interface PaymentProvider {
  name: string; // "dodo" | "whop" | "helio" | "depay" | "nowpayments"
  rail: PaymentRail;
  // create checkout/session, returns URL to redirect user to
  createCheckout(req: PaymentRequest): Promise<{ checkoutUrl: string; providerRef: string }>;
  // webhook handler verifies signature and returns PaymentResult
  handleWebhook(rawBody: Buffer, headers: Record<string, string>): Promise<PaymentResult>;
  // for crypto: verify tx hash on-chain
  verifyOnChain?(txHash: string, expectedUsd: number): Promise<PaymentResult>;
}
