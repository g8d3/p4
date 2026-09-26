# e076 — Bookmark Product (agent-run)

Sellable X-bookmark backup: local-first Chrome extension + backend + API/MCP.
Agent loop builds everything. Human only does KYC/money, domains, social
accounts, and pastes API keys when the ops page asks.

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, notify
- [../e064-x-bookmarks/AGENTS.md](../e064-x-bookmarks/AGENTS.md) — signal pipe context (internal, not for sale)
- [../e062-agent-ops/DIRECTIVES.md](../e062-agent-ops/DIRECTIVES.md) — runner rules

## Layout
- `AGENTS.md` — this file
- `sites/landing/` — merchant-review-ready site (index, pricing, terms, privacy, refunds, contact)
- `ops/cycle.html (Keys tab)` — agent-cycle page: human-gating table + key entry (localStorage only, never committed)
- `ops/needs.json` — machine-readable list of what the human must provide
- `loop/run.sh` + `loop/state.json` — agent cycle runner (builder/QA/growth/billing)
- `ag-01/` — builder agent work (extension spec, backend, referrals, crypto)

## Human-gating rule (hard)
- Agent never creates KYC accounts, never holds fiat credentials, never
  publishes social posts without approved keys.
- Secrets live in browser localStorage or `~/.secrets/.env`, never in repo.
- Ops dashboard is the single place that tells the human what to paste,
  with links and status. See `ops/needs.json`.

## White-label rule (owner standing rule)
- This page is the ADMIN/owner view. End tenants will see a branded
  subset, never this. Every feature ships with: what admin sees vs
  what tenant sees, per-tenant branding config (name, logo, colors,
  domain), per-tenant keys/plans isolation.
- Admin installs the extension FREE (owner build, direct download).
  Tenants get it via store listing or tenant link per plan.

## UX law (owner standing rule, applies to every future decision)
- Mobile-first: owner uses Quetta (extension-capable mobile browser).
  Every page AND the Chrome extension UI must work on mobile + desktop.
- Thumb zone: ALL navigation/tab bars fixed at the BOTTOM of the screen.
  No top nav, no exceptions. No per-page nav bars either — the hub bottom
  bar is the only nav. Content pages get bottom padding so it never covers text.
- Compact bars: tab labels max 2 short words + count (e.g. `Todo 5`, not
  `Blocked (5)`). 13px, single row, no wrap, no horizontal overflow at 390px.
- No in-content links to pages that have a tab: the bottom bars are the only
  navigation. In-page calls-to-action become buttons that activate the tab.
  External links (Stripe, docs) stay.
  Every frontend fix is verified in agent-browser at 390x844 (emulated mobile)
  with geometry eval + screenshot BEFORE claiming done.
- Async work (legs): verify START in seconds (running row visible), keep
  working, confirm finish later. Never block on long sleeps.
- Button size stays as-is until owner says otherwise.

## DONE ladder
1. SCAFFOLD — landing + ops dashboard render locally.
2. MERCHANT-READY — public URL, terms/privacy/refunds/contact, pricing matches checkout.
3. KEYS-WIRED — fiat merchant + crypto merchant webhooks verified in test mode.
4. REFERRALS — cookie attribution + payout hold working.
5. SELLING — first paid user.
