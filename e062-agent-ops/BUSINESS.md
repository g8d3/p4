# BUSINESS — the clone-the-tollbooth doctrine

Vision: any person, no technical skill needed, runs a fleet of agents
that produces value for other agents and people — machine customers
paying machine money (USDC, no KYC) for structured, reliable APIs.

## Rules derived from it

1. **Every paid gate blocking us is a build target.** Loris API ($79+),
   LunarCrush ($90+), Kaito ($833+) → own production versions from
   public/direct sources. Proven pattern: intercept → understand →
   rebuild venue-direct (never resell their feed; compute our own facts).
2. **Model routing (owner order 2026-09-12): current model first.** Runner legs use `opencode-go/muse-spark-1.3-contributor` (practically unlimited) via `$E062_MODEL_ARGS` (override to route cheap/frontier). Quota watch (`zai-usage`) stays as fallback discipline.
3. **Trials are legitimate evaluation, never farming.** Real details,
   real cancellations, one account per service. Every trial logged with
   renewal date; ntfy reminds before charge day; monthly kill-or-keep.
4. **Extraction line**: public facts + interoperability OK; breaking
   access controls, sharing credentials, or republishing proprietary
   feeds verbatim is out. Same rule as code.
5. **Accounts**: SPEND.md green/yellow/red stands. Humans only where
   law/ToS requires a person (KYC, fiat). Everything else: agent-run.
6. **Build MCP-first.** LunarCrush already sells MCP access — validation.
   Our APIs (funding, multiples, velocity) ship REST + MCP so *agents*
   are first-class customers, priced per-call in USDC.
