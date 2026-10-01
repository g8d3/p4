# e085 — Swarm Marketplace (sell / rent agent swarms)

Web app where anyone can sell or rent swarms of agents.
Sellers publish a swarm; buyers rent or buy; platform takes a fee.
Built BY a swarm of agents (see Builder Swarm below).

## Product

| Surface | User action |
|---|---|
| `/` marketplace | Search swarms, filter by pricing model, open detail, rent/buy (mock checkout), publish your own swarm. |
| `/api/swarms` | List + create swarms (JSON file store). |
| `/api/orders` | Rent/buy a swarm under a pricing model. |
| `/api/domain-check?name=` | RDAP read-only check (404 = likely free, confirm at checkout). |
| `/api/needs` | What the app still needs (needs-herald agent writes here). |
| Provisioning panel (in page) | Email / domain / API-keys checklist per buyer/seller. |
| Auth panel (in page) | Google login WITHOUT Google Cloud fiddling → Clerk shared OAuth (dev keys). |

## Pricing models (v0)

- `per_result` — pay only on accepted result ($/result).
- `per_token` — metered ($/1k tokens).
- `per_run` — flat per execution.
- `per_seat_month` — rent seats monthly.
- `one_time` — buy outright.
- `revenue_share` — % of downstream earnings.
- Ideas backlog: pay-per-success + tip jar, stake/slash escrow, auction,
  freemium quota, usage-credit bundles.

## Architecture

```
server/app.py       stdlib only (threaded http.server) + /api/*
  /api/health       alive + counts
  /api/swarms       GET list / POST publish
  /api/orders       GET list / POST rent-buy {swarm_id, model, qty}
  /api/domain-check GET ?name=foo.bar -> RDAP status (no purchase)
  /api/needs        GET checklist the app still needs
  /api/events       POST telemetry {type, detail}
public/index.html   single-file UI, zero deps
data/swarms.json    seed swarms (file store)
data/orders.jsonl   orders log
data/needs.json     needs-herald output
needs.json          ALL machine values: port, base url envs, fee bps, auth provider
bin/serve.sh        start server on port from needs.json
test/check.sh       API smoke + JS syntax
```

Rule: stdlib only, no deps. All machine values from env/settings
documented in `needs.json` — never buried in code.

## Builder Swarm (agents that build this app)

| Agent | Job | Output |
|---|---|---|
| domain-scout | Search + rank domain names (RDAP only, no purchase) | `data/domains.md` |
| provisioner | Email/domain/API-keys provisioning paths (Resend, Porkbun, Clerk) | provisioning panel + docs |
| inference-scout | Compare OpenCode Zen + Claude Code vs cheaper/better (OpenRouter, Together, Fireworks, Groq, Gemini) on cost + features | `data/inference.md` |
| needs-herald | Watches repo, tells team what else the web app needs | `GET /api/needs` |
| auth-simplifier | Google auth with zero Google Cloud console work | Clerk shared-OAuth integration doc |
| marketplace-builder | Core buy/sell/rent + checkout mock + fee math | `server/app.py` + UI |

## Run

```bash
bash bin/serve.sh            # port from needs.json (default 8335)
curl -sk https://127.0.0.1:8335/api/health
bash test/check.sh           # GATE GREEN = health + models + order + accept + review + trial + seller
```

v1 serves **HTTPS** on `0.0.0.0` via the box tailnet cert
(`~/.config/e062/tail.crt`) when present, plain HTTP otherwise.
Tailnet URL: `https://vuos-hcar5000mi.tail6918b0.ts.net:8335/`.
Sales sheet: `SELL.md` — demo script, fee math, handover checklist.

## Auth decision (no Google Cloud fiddling)

Use **Clerk** (shared Google OAuth dev keys): create a Clerk app, enable
Google, use `VITE_CLERK_PUBLISHABLE_KEY` in frontend — no GCP project,
no OAuth consent screen, no client secret. Migrate to own GCP keys only
when going to production. Alternatives ranked: Clerk > Auth0 social
(dev keys) > Supabase (needs own GCP keys — rejected for v0).

## Inference default (until scout reports)

Default: **OpenCode Zen** (`OPENCODE_API_KEY`, base from needs.json).
"command code" is read as **Claude Code / Anthropic API** pending owner
confirm. Scout compares both vs OpenRouter/Together/Fireworks/Groq on
$/1M tok + features (tools, batch, cache) and the winner becomes default.

## DONE ladder

1. WORKING — done (v1: escrow lifecycle, reviews, trials, seller desk, HTTPS). check.sh GATE GREEN.
2. DEPLOYED — done (tailnet HTTPS live, browser-verified). Reboot line documented in SELL.md (cron paused by owner).
3. TESTED — scripted-browser: search, detail, rent, publish, domain-check.
4. ANNOUNCED — owner ping with URL.
5. MONETIZED — platform fee live (see needs.json `fee_bps`).
