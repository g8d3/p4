# Auth: Google login with zero Google Cloud console — VERIFIED

Claim: TRUE for dev. Clerk dev instances ship shared Google OAuth keys.
No GCP project, consent screen, or client secret needed until production.

## 5-minute setup
1. Sign up at https://dashboard.clerk.com (2 min). Create app, name it
   `swarm-marketplace`, pick Google as a sign-in method.
2. In Clerk dashboard: Configure → SSO Connections → Google → Enable.
   Leave default shared dev credentials untouched (1 min).
3. Copy the publishable key: API Keys → `pk_test_...` (30 sec).
4. Set env and restart (30 sec):
   `export CLERK_PUBLISHABLE_KEY=pk_test_... && bash bin/serve.sh`
5. Open `/`, click "Continue with Google" → real Google popup.
   Remove mock handler in `public/index.html` once key is set (1 min).

## Env
| Var | Value | Where |
|---|---|---|
| `CLERK_PUBLISHABLE_KEY` | `pk_test_...` | frontend (`needs.json: auth.publishable_key_env`) |

## Limits (why dev-only)
- Shared keys work on dev instances + localhost only, show Clerk branding.
- Cap ~100 monthly active users; fine for v0.
- Production: Bring-Your-Own GCP OAuth client (Clerk docs → "Use custom
  credentials"), swap to `pk_live_...`. No code change.

## Rejected for v0
- Supabase / Auth.js / NextAuth Google provider: require own GCP client
  ID + secret on day one. Auth0: dev keys exist but heavier setup.
