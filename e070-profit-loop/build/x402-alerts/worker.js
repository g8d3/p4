/* e070 x402-alerts v2 (supervised pilot): sells funding-rate alerts for USDC per call.
   GET /        -> landing (price, terms, how to pay)
   GET /alerts  -> 402 + PAYMENT-REQUIRED (x402 v2) when unpaid;
                    200 alerts JSON ONLY after facilitator /verify says valid.
   Flow on X-PAYMENT / PAYMENT-SIGNATURE header:
     1. base64+JSON decode            -> else 402 (undecodable)
     2. structural match vs our terms -> else 402 (mismatch; no network call)
     3. POST facilitator /verify {paymentPayload, paymentRequirements}
        (server-side fetch; free read, no wallet, no keys) -> invalid/error => 402
     4. POST facilitator /settle (same body) -> outcome recorded in
        PAYMENT-RESPONSE; settle failure => 402 (fail closed, no free payload).
   Price: $0.05 USDC on Arbitrum (50000 base units, 6 decimals).
   Facilitator: public https://x402.org/facilitator (no key, free). It currently
   serves testnets only ("No facilitator registered" for exact/eip155:42161),
   so mainnet payments fail CLOSED (402) until the owner points FACILITATOR_URL
   at the Coinbase CDP facilitator (needs CDP API key -> owner-run secret).
   Settle is executed by the FACILITATOR (broadcasts the buyer's signed
   transferWithAuthorization; moves buyer USDC -> payTo). This worker holds no
   keys and submits no transactions itself. $0 inference, no spending.
   No secrets, no KV in code. */
const PAY_TO = '0x66465C408eD80708ECcDaA3c1f0BD48C8E4f5156';
const ARB_USDC = '0xaf88d065e77c8cC2239327C5EDb3A432268e5831';
const NETWORK = 'eip155:42161';
const AMOUNT = '50000'; // $0.05 USDC, 6 decimals
const PRICE_USD = '0.05';
const FACILITATOR_DEFAULT = 'https://x402.org/facilitator';

// Static SAMPLE snapshot (e058 sampler halted 2026-09-15, cron paused repo-wide).
const SAMPLE = {
  snapshot_ts: '2026-09-15T08:47:46Z',
  freshness: 'STALE (~3d old at build; e058 sampler halted Sep 15)',
  spreads: [
    { coin: 'LSK', long_v: 'variational', short_v: 'aster', spread_bps_8h: 165.17, apy_pct: 3136.7, oi_rank: 86, persist: '4/4' },
    { coin: 'ACE', long_v: 'hyperliquid', short_v: 'aster', spread_bps_8h: 104.54, apy_pct: 2385.7, oi_rank: 145, persist: '4/4' },
    { coin: 'HIVE', long_v: 'extended', short_v: 'vest', spread_bps_8h: 86.78, apy_pct: 1013.0, oi_rank: 445, persist: '4/4' },
  ],
  note: 'T 3975% APY excluded (decay trap: 10392%->3975%); OI rank < 500 gated.',
};

function requirementObject() {
  return {
    scheme: 'exact',
    network: NETWORK,
    amount: AMOUNT,
    asset: ARB_USDC,
    payTo: PAY_TO,
    maxTimeoutSeconds: 300,
    extra: { name: 'USDC', version: '2' },
  };
}

function paymentTerms(url) {
  return {
    x402Version: 2,
    error: 'PAYMENT-SIGNATURE header is required',
    resource: {
      url,
      description: 'Top persistent funding-rate spreads (long/short venues, bps, APY, OI rank)',
      mimeType: 'application/json',
    },
    accepts: [requirementObject()],
    // Bazaar-style input/output schema so discovery indexers (x402scan)
    // can mark this endpoint invocable. GET takes no inputs: the query
    // schema is honestly empty; the output example mirrors the real payload.
    extensions: {
      bazaar: {
        info: {
          name: 'Funding-rate alerts',
          description: 'Top persistent funding-rate spreads, $0.05 USDC per call on Arbitrum via x402.',
        },
        schema: {
          properties: {
            input: {
              properties: {
                queryParams: { type: 'object', properties: {} },
              },
            },
            output: {
              properties: {
                example: {
                  status: 'SAMPLE',
                  snapshot_ts: SAMPLE.snapshot_ts,
                  spreads: [{ coin: 'LSK', long_v: 'variational', short_v: 'aster', spread_bps_8h: 165.17, apy_pct: 3136.7 }],
                },
              },
            },
          },
        },
      },
    },
  };
}

const b64 = (s) => btoa(unescape(encodeURIComponent(s)));
const unb64 = (s) => decodeURIComponent(escape(atob(s.trim())));

function requires402(url, extraBody) {
  const terms = paymentTerms(url);
  return new Response(
    JSON.stringify({
      // Dual transport: v2 terms in the PAYMENT-REQUIRED header (primary)
      // AND v1-style accepts JSON in the body (legacy-compat probes that
      // parse the body instead of the header, e.g. x402scan).
      x402Version: 2,
      accepts: terms.accepts,
      resource: terms.resource,
      extensions: terms.extensions,
      error: 'payment_required',
      hint: 'Pay $0.05 USDC on Arbitrum to ' + PAY_TO + ' via x402 (exact scheme). Any x402 v2 client works; verified server-side via the facilitator. Retry with X-PAYMENT (or PAYMENT-SIGNATURE) header carrying the signed payload. No signup.',
      price_usd: PRICE_USD,
      asset: 'USDC',
      chain: 'arbitrum',
      network: NETWORK,
      asset_contract: ARB_USDC,
      pay_to: PAY_TO,
      facilitator: FACILITATOR_DEFAULT,
      ...(extraBody || {}),
    }),
    {
      status: 402,
      headers: {
        'Content-Type': 'application/json',
        'PAYMENT-REQUIRED': b64(JSON.stringify(terms)),
      },
    }
  );
}

// Structural pre-check vs our exact terms (rejects garbage with no network call).
// Accepts v2 shape ({accepted:{...}}) or flat ({scheme,network,amount,...}).
function acceptedTerms(payload) {
  return payload.accepted || payload.accept || payload.payment || payload;
}
function payloadMatchesTerms(payload) {
  try {
    const p = acceptedTerms(payload);
    const amt = BigInt(p.amount ?? '0');
    return (
      (p.scheme || payload.scheme) === 'exact' &&
      (p.network || payload.network) === NETWORK &&
      amt >= BigInt(AMOUNT) &&
      (p.asset || '').toLowerCase() === ARB_USDC.toLowerCase() &&
      (p.payTo || p.pay_to || '').toLowerCase() === PAY_TO.toLowerCase()
    );
  } catch {
    return false;
  }
}

async function facilitatorCall(env, path, paymentPayload, signal) {
  const base = (env && env.FACILITATOR_URL) || FACILITATOR_DEFAULT;
  const headers = { 'Content-Type': 'application/json' };
  if (env && env.FACILITATOR_AUTH) headers['Authorization'] = env.FACILITATOR_AUTH;
  const res = await fetch(base + path, {
    method: 'POST',
    headers,
    signal,
    body: JSON.stringify({
      x402Version: 2,
      paymentPayload,
      paymentRequirements: requirementObject(),
    }),
  });
  const txt = await res.text();
  try {
    return { status: res.status, body: JSON.parse(txt) };
  } catch {
    return { status: res.status, body: { raw: txt.slice(0, 300) } };
  }
}

const LANDING = `<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Funding-rate alerts — $0.05 per call (x402)</title>
<link rel="icon" href="/favicon.ico" type="image/svg+xml">
<style>body{font-family:system-ui;max-width:640px;margin:0 auto;padding:20px;line-height:1.5;color:#1c1a15;background:#f6f4ee}
.card{background:#fff;border:1px solid #e6e1d4;border-radius:14px;padding:16px;margin-bottom:12px}
code{background:#eee;border-radius:6px;padding:1px 6px;font-size:13px}</style></head><body>
<h1>Funding-rate alerts</h1>
<p>Top persistent spreads, wallet-to-wallet. <b>$0.05 USDC</b> per call on <b>Arbitrum</b>. No signup, no keys. Every paid call is verified server-side via the x402 facilitator before the payload is served.</p>
<div class=card><b>Endpoint</b><br><code>GET /alerts</code> with an x402 payment (<code>X-PAYMENT</code> header). Unpaid calls get <code>402</code> + <code>PAYMENT-REQUIRED</code> terms.</div>
<div class=card><b>Terms</b><br>Price <code>$0.05</code> · Asset <code>USDC</code> · Chain <code>arbitrum (eip155:42161)</code><br>USDC <code>${ARB_USDC}</code><br>Pay to <code>${PAY_TO}</code></div>
<div class=card>Feed status: <b>SAMPLE</b> — static snapshot 2026-09-15 (e058 sampler halted; cron paused). Labeled as such in every payload until the live feed resumes.</div>
</body></html>`;

// x402scan DISCOVERY.md compat shape: {version, resources[]} fan-out.
function discoveryDescriptor(url) {
  return {
    version: 1,
    resources: [url + '/alerts'],
  };
}

function openapiDoc(url) {
  return {
    openapi: '3.0.0',
    info: {
      title: 'Funding-rate alerts (x402)',
      version: '2.0.0',
      description: 'Top persistent funding-rate spreads, $0.05 USDC per call on Arbitrum via x402. Unpaid GET /alerts returns 402 + PAYMENT-REQUIRED terms; paid calls are verified server-side via the facilitator (/verify) and executed via /settle before the payload is served.',
      contact: { name: 'Focalis', email: 'hola@focalis.cc' },
      'x-guidance': 'GET /alerts is paid ($0.05 USDC on Arbitrum via x402): call unpaid, read the 402 challenge (PAYMENT-REQUIRED header or accepts body), pay, retry with X-PAYMENT header. / and /openapi.json are free.',
    },
    servers: [{ url }],
    components: {
      securitySchemes: {
        x402: {
          type: 'apiKey',
          in: 'header',
          name: 'X-PAYMENT',
          description: 'x402 v2 payment: base64 signed exact-transfer payload (USDC on Arbitrum). Unpaid calls get 402 with terms.',
        },
      },
    },
    paths: {
      '/alerts': {
        get: {
          summary: 'Funding-rate alerts (paid, x402, facilitator-verified)',
          description: 'Returns 402 + PAYMENT-REQUIRED terms when unpaid or unverifiable; 200 alerts JSON only after facilitator /verify isValid and /settle succeeds.',
          security: [{ x402: [] }],
          'x-payment-info': {
            protocols: ['x402'],
            price: { mode: 'fixed', currency: 'USD', amount: '0.05' },
          },
          responses: {
            200: { description: 'Alerts JSON (SAMPLE snapshot until live feed resumes)' },
            402: { description: 'payment_required — pay $0.05 USDC on Arbitrum via x402, retry with X-PAYMENT header' },
          },
        },
      },
      '/openapi.json': {
        get: {
          summary: 'OpenAPI document (free)',
          security: [],
          responses: { 200: { description: 'This OpenAPI document' } },
        },
      },
      '/': {
        get: {
          summary: 'Landing (price, terms, how to pay)',
          security: [],
          responses: { 200: { description: 'HTML landing page' } },
        },
      },
    },
  };
}

const FAVICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><circle cx="16" cy="16" r="13" fill="none" stroke="#1c1a15" stroke-width="2"/><ellipse cx="16" cy="16" rx="6" ry="13" fill="none" stroke="#1c1a15" stroke-width="1.5"/><line x1="3" y1="16" x2="29" y2="16" stroke="#1c1a15" stroke-width="1.5"/></svg>`;

const json = (o) => new Response(JSON.stringify(o), { headers: { 'Content-Type': 'application/json' } });

async function handle(req, env) {
  const u = new URL(req.url);
  if (u.pathname === '/favicon.ico') return new Response(FAVICON_SVG, { headers: { 'Content-Type': 'image/svg+xml', 'Cache-Control': 'public, max-age=86400' } });
  if (u.pathname === '/.well-known/x402') return json(discoveryDescriptor(u.origin));
  if (u.pathname === '/openapi.json') return json(openapiDoc(u.origin));
  if (u.pathname === '/alerts') {
    const sig = req.headers.get('X-PAYMENT') || req.headers.get('PAYMENT-SIGNATURE') || req.headers.get('PAYMENT-PAYLOAD');
    if (!sig) return requires402(u.origin + '/alerts');
    let payload;
    try {
      payload = JSON.parse(unb64(sig));
    } catch {
      return requires402(u.origin + '/alerts', { detail: 'undecodable payment header' });
    }
    if (!payloadMatchesTerms(payload)) {
      return requires402(u.origin + '/alerts', { detail: 'payment does not match terms (exact / arbitrum / 0.05 USDC / payTo)' });
    }
    // Server-side facilitator verification (free read; worker holds no keys).
    let v;
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 9000);
      try {
        v = await facilitatorCall(env, '/verify', payload, ctl.signal);
      } finally {
        clearTimeout(t);
      }
    } catch (e) {
      return requires402(u.origin + '/alerts', { detail: 'facilitator verify unreachable: ' + (e && e.name === 'AbortError' ? 'timeout' : 'network-error') });
    }
    if (!v.body || v.body.isValid !== true) {
      const reason = (v.body && (v.body.invalidReason || v.body.error)) || 'unverifiable';
      const msg = (v.body && (v.body.invalidMessage || v.body.error)) || '';
      return requires402(u.origin + '/alerts', { detail: 'facilitator rejected payment', facilitator_reason: String(reason), facilitator_message: String(msg).slice(0, 200) });
    }
    // Verified: execute via facilitator /settle, then serve. Settle failure => 402 (fail closed).
    let s;
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 15000);
      try {
        s = await facilitatorCall(env, '/settle', payload, ctl.signal);
      } finally {
        clearTimeout(t);
      }
    } catch {
      return requires402(u.origin + '/alerts', { detail: 'facilitator settle unreachable after valid verify; retry' });
    }
    if (!s.body || s.body.success !== true) {
      const reason = (s.body && (s.body.errorReason || s.body.error)) || 'settle-failed';
      return requires402(u.origin + '/alerts', { detail: 'payment verified but not settled; retry (no payload served)', facilitator_reason: String(reason) });
    }
    return new Response(
      JSON.stringify({
        status: 'SAMPLE',
        feed: 'static snapshot until live feed resumes',
        snapshot_ts: SAMPLE.snapshot_ts,
        freshness: SAMPLE.freshness,
        spreads: SAMPLE.spreads,
        note: SAMPLE.note,
        price_paid_usd: PRICE_USD,
      }),
      { headers: { 'Content-Type': 'application/json', 'PAYMENT-RESPONSE': b64(JSON.stringify({ success: true, transaction: s.body.transaction || '', network: s.body.network || NETWORK })) } }
    );
  }
  return new Response(LANDING, { headers: { 'Content-Type': 'text/html;charset=utf-8' } });
}
export default { fetch: (req, env) => handle(req, env) };
