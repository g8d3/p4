# ag-02 — Digital product creation skills research

Research agent for e032 Stage 1. Maps what AI agents can ACTUALLY do today to
build digital products (web apps, saas, tools, templates, ebooks, courses) —
with verified cloud providers, prices, free tiers, and the cloud-first rule.

## Agent id
`ag-02-products` — use this in all Cadence heartbeats and file names.

## Cadence
- Expected check interval: 60s while WORKING, extend to 120s during long provider-comparison reads.
- Call `report.sh ag-02-products "<current step>"` at every milestone and after every long command.
- Write ALL deliverables to `output/`. The monitor also watches that directory.

## Inherits
- [../../AGENTS.md](../../AGENTS.md) — experiment scope, Stage 1 contract
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern, Open Design, dsh, browser automation

## Agent-specific mission

Produce `output/skills-products.md`, `output/recommendations.md`, `output/timings.log`, `output/done.txt`.

Cover:

1. **Agent-native development stacks** — how coding agents ship real products:
   web frameworks, hosting/deployment (Vercel, Cloudflare, Fly, Railway),
   databases, auth, payments. Open Design (e027) for design-in-code, dsh-style
   harnesses (e028), and the mobile-first p4 working environment.
2. **Cloud services over local pain** — detect the dependencies/build issues
   that plague local dev (native modules, npm allowScripts, GPU quirks) and
   give the cloud solution instead (serverless, managed DB, managed GPU).
   Provide a decision table: task → local pain → cloud solution → price/free tier.
3. **Speed of delivery** — realistic end-to-end timeline for an agent-built
   product (idea → landing → signup → payment → v1) and the pitfalls that
   actually slow agents down (permission hangs, model limits, context loss).
4. **Profit potential** — what kinds of digital products are fastest to ship
   and monetize with agent assistance (templates, tools, niche saas, content
   products).

**Price/quality honesty**: verify at least 3 provider/link claims directly.
Mark each entry `[verified]` or `[unverified]`.

## Deliverables
- `output/skills-products.md` — full skill map
- `output/recommendations.md` — top 3-5 highest-leverage skills + cloud choices
- `output/timings.log` — timings of every command
- `output/done.txt` — headline findings + verdict

## Rule compliance
- Cloud-first; measurement-based timeouts; 60 min deadline.

## Notify
- On finish: `notify.sh done "ag-02 product skills research finished: <headline>"`
- On failure: `notify.sh error "ag-02 failed: <cause>"`

## Self-command
- Every blocking command runs in background: `> /dev/null 2>&1 &`
- Self-wake: `tmux send-keys -t 32-2 "check status" Enter`
- `(sleep <mean+4σ>; tmux send-keys -t 32-2 "Self-wake: step=N, check" Enter) &`