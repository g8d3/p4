# RSC Findings — Higgsfield Image Generation

## Discovery

Both mobile (`/mobile/image/`) and desktop (`/ai/image`) versions of Higgsfield use **Next.js RSC (React Server Components)** to trigger image generation. There is no client-side POST to `/fnf/jobs/` in either version.

The flow is:

```
[Click Generate] → RSC navigation (GET _rsc=...) → Next.js server → fnf-api-gw → job created
```

The actual API call (`POST /fnf/jobs/seedream-v4-5`) happens **server-to-server** between Next.js and the API gateway, not in the browser. The browser only sees a navigation request with `_rsc=` parameter.

## Why this matters

### Advantages of RSC

| Aspect | Description |
|--------|-------------|
| **Auth** | Clerk session token stays server-side, never exposed to client JS |
| **DataDome** | Anti-bot headers are handled server-side, cleaner client code |
| **Payload** | Server sends only the result (update UI), not the entire response |
| **Latency** | Single round-trip: click → server processes → UI updates |

### Disadvantages (for automation)

| Aspect | Description |
|--------|-------------|
| **No API endpoint** | No direct `POST /fnf/jobs/` we can call — the generation is triggered by a RSC navigation |
| **RSC protocol** | Next.js RSC uses binary streaming, not JSON. Hard to reverse-engineer |
| **Server version** | The RSC payload format changes between Next.js versions |
| **State coupling** | Form state (prompt, model, aspect) is sent as serialized React state, not simple form fields |
| **No idempotency** | An RSC navigation is not a clean API call — it carries UI state, route data, etc. |

### Current status

- `higgsfield-gen` (browser automation via mobile) works reliably in ~3-5s per image
- Direct API without browser is not feasible without reverse-engineering RSC binary protocol

## RSC binary protocol (why it's complex)

Next.js RSC payload is NOT JSON. It's a custom binary format:

```
1:I[React component data]
2:J[serialized props]
3:E[event handlers]
```

This is streamed incrementally. To make a raw RSC request you'd need to:
1. Serialize the form state as React Fiber data
2. Encode it in the RSC binary format
3. POST to the Next.js endpoint with correct headers
4. Parse the binary response to extract job ID and status

This is fragile per Next.js version and not documented.
