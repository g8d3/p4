# LIMITS — the 6 standing targets

Owner directive: the loop must systematically escape AI limitations —
ToS-compliant, no spam — and each escape becomes a business.

**Standing rule (all 6): account CREATION stays human.** Agents prepare
everything up to the click (copy, assets, forms pre-filled, checkout links
assembled) and stop at `[NEEDS OWNER TAP]`. Agents never create accounts,
never bypass logins, never post/send/spend on their own.

**Loop contract:** e082's tick backlog source pulls e083 gaps AND the open
checkboxes below — parse open `- [ ]`, attempt the smallest shippable slice,
log evidence. A checked `- [x]` box means acceptance proof is on disk and the
loop skips it.

## Open items (loop-readable — keep this exact format)

- [ ] [limits-l1] One-per-site accounts without violating ToS — stage credentials + recovery kit, owner taps Create
- [ ] [limits-l2] Profile assets agents can generate + stage — pfp/cover/bio pack ready for owner upload
- [ ] [limits-l3] Posting through owner-minted keys/sessions — drafts queued, only owner-approved rows publish
- [ ] [limits-l4] Undetectable browser — kill the webdriver tell, headed/Xvfb path proven on this box
- [ ] [limits-l5] Domain + decentralized serving without agent-held payment — owner-bought domain, free-tier hosting
- [ ] [limits-l6] More AI inference — owner keys, free tiers, local models wired through one endpoint slot

---

### (L1) One-per-site accounts without violating ToS

- **ToS guardrail:** one account per site, created by the human in their own
  browser; agents never script signup forms, never solve captchas, never
  operate throwaway armies. What's allowed: researching which site/plan fits,
  drafting usernames/bios, preparing recovery kits. What stays human-tap:
  clicking Create, solving any captcha, entering phone/2FA.
- **Agent-side:** site shortlist + username availability notes (read-only
  checks), draft profile copy, recovery-kit checklist (password manager entry
  template, 2FA reminder, recovery email note).
- **Human-tap:** the Create click + any verification challenge.
- **Acceptance proof:** `log/limits.log` shows a staged kit (site, handle,
  bio draft, checklist) with zero signup POSTs issued by any agent; owner
  confirms the tap took < 5 min.
- **Business:** *Handle Concierge* — $19 setup + $5/mo per managed identity:
  who pays: solo founders wanting clean one-per-site presence; for what:
  staged kits + renewal/reminder hygiene. No spam, no multi-accounting.

### (L2) Profile assets agents can generate + stage

- **ToS guardrail:** generated pfp/cover/bio are original assets (no scraped
  photos, no impersonation of real people). Allowed: AI/templated graphics,
  original bio copy. Human-tap: the Upload/Save click on each site.
- **Agent-side:** generate pfp (1024px), cover (1500×500), bio ≤160 chars +
  long version; stage as a dated pack under `assets/` with a preview page.
- **Human-tap:** uploading the pack to the site created in L1.
- **Acceptance proof:** a staged pack on disk + preview screenshot; owner
  uploads without edits.
- **Business:** *Instant Brand Pack* — $9/pack or $29/mo unlimited: who pays:
  new accounts/communities; for what: ready-to-upload identity packs.

### (L3) Posting through owner-minted keys/sessions

- **ToS guardrail:** agents only ever publish through credentials the owner
  minted (API keys, logged-in sessions on this box) and only content rows the
  owner approved. No credential harvesting, no session-cookie export to other
  machines (session-theft flag risk — see e020). Scheduler posts approved rows
  only; unapproved drafts wait forever.
- **Agent-side:** draft queue with `approved:false` default, fact-attached
  copy (every claim cites a live number), one-pending-draft dedupe.
- **Human-tap:** minting the key/session, pressing Approve (or writing the
  auto-approve rule).
- **Acceptance proof:** e083 pattern live — draft queued `source:loop`,
  `approved:false`, never auto-posted; owner Approve → posted.
- **Business:** *Approval-Gated Autoposter* — $12/mo per channel: who pays:
  small shops wanting daily posts; for what: drafted, fact-checked queue where
  they tap once and the week is scheduled.

### (L4) Undetectable browser (kill the webdriver tell, headed/Xvfb path)

- **ToS guardrail:** undetectability is for OUR sites and consenting test
  targets only — passing our own bot-noise filters, screenshotting our own
  funnel. Never for bypassing third-party bot walls, ticket scalping, review
  spam, or credential stuffing. Research spike: `bot.sannysoft.com` (a
  consenting detector page) + our own pages only.
- **Agent-side:** headed-under-Xvfb launch path, stealth flags, detection
  re-score after each change; all flags documented in BROWSER-CAPABILITY.md.
- **Human-tap:** none routinely — but any new third-party target needs owner
  sign-off before first visit.
- **Acceptance proof:** headed run re-scores `bot.sannysoft.com` with
  `navigator.webdriver=false` (or documented residual tells); exact launch
  flags in BROWSER-CAPABILITY.md; prior art e020 + headless baseline kept.
- **Business:** *Bot-Wall Audit* — $49/audit or $99/mo monitoring: who pays:
  site owners failing legit users at bot walls; for what: headed/headless
  detection scorecards + fix list. We sell the measurement, not the bypass.

### (L5) Domain + decentralized serving without agent-held payment

- **ToS guardrail:** agents never hold payment credentials, never complete
  checkout. Allowed: RDAP availability checks (read-only), price comparison,
  DNS/hosting wiring AFTER the owner buys. Purchase + account creation stay
  human-tap.
- **Agent-side:** ranked shortlist with RDAP status + renewal prices
  (DOMAINS.md pattern), post-purchase wiring (DNS records, TLS check,
  `public_url` in needs.json), free-tier/decentralized serving notes.
- **Human-tap:** registrar account + checkout + DNS buy-click.
- **Acceptance proof:** owner-bought domain resolving to this box (or URL
  forward), TLS green, `needs.json public_url` set; zero agent-issued
  payment calls.
- **Business:** *Launch Wiring* — $25 one-time per domain: who pays: anyone
  from L1–L3 with a brand; for what: registrar shortlist + full wiring +
  TLS proof. Renewals stay theirs.

### (L6) More AI inference (owner keys, free tiers, local models)

- **ToS guardrail:** inference only through owner-minted keys, published free
  tiers within their rate limits, or local models on this box. No key sharing,
  no quota-pool abuse, no scraping someone else's endpoint. Spend ledger stays
  honest (simulated vs real flagged — see needs.json `real_spend_tracking`).
- **Agent-side:** one endpoint slot (`llm_model_endpoint` in needs.json),
  provider comparison (price/latency/free-tier), Jev-as-judge pattern for
  browser-test agents (JEV.md), local-model fallback notes.
- **Human-tap:** creating the provider account + minting the key + pasting it
  into settings.
- **Acceptance proof:** a tick that calls the endpoint slot and logs
  tokens/cost to the ledger; free-tier usage under quota with 429s handled by
  backoff, never by key rotation tricks.
- **Business:** *Inference Concierge* — $10/mo per workspace: who pays: agent
  tinkerers; for what: cheapest-fit provider routing + quota dashboards +
  local fallback. Margin is saved spend, transparently metered.
