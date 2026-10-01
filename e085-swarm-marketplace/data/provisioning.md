# Provisioning paths (no servers to run)

All machine values come from env, listed in `needs.json`. Never hardcode.

## 1. Email via Resend (receipts + magic links)
1. Sign up at https://resend.com → API Keys → create key `re_...`.
2. `export RESEND_API_KEY=re_...` (add to shell rc / host env).
3. Verify one sender domain or use onboarding address for dev.
4. App sends order receipts + magic links with that key only. No SMTP server.

## 2. Domain via Porkbun (cheap + free DNS/SSL)
1. Search name in-app: `GET /api/domain-check?name=foo.com` (RDAP only,
   404 = likely free — always confirm at registrar).
2. Buy at https://porkbun.com (no API key needed for v0 manual buy).
3. Point DNS: Porkbun nameservers or Cloudflare free → host IP.
   TLS comes free from host/proxy; no cert to manage by hand.
4. `export E085_PUBLIC_URL=https://your.domain && bash bin/serve.sh`.

## 3. API keys via env / needs.json
| Key env | Purpose | Required |
|---|---|---|
| `CLERK_PUBLISHABLE_KEY` | Google login (see `data/auth.md`) | for real login |
| `RESEND_API_KEY` | email receipts / magic links | for real email |
| `E085_PORT` / `E085_PUBLIC_URL` | port + public URL (see `needs.json`) | optional |
| `OPENCODE_API_KEY` | inference default (scout compares) | sellers only |
| `ANTHROPIC_API_KEY` | Claude Code path, pending confirm | optional |

Checklist: `GET /api/needs` shows what is still missing. UI panel
mirrors it; page stays usable in mock mode until keys are set.
