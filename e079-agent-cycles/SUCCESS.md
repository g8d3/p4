# SUCCESS — what winning means for e079

Owner definition (2026-09-28). Success is margin, not traffic.

1. **People pay more than it costs to run** — revenue covers infra + AI costs with room to spare.
2. **Margin grows**, or stays **above our niche average** — ideally niche average + n stdevs.
3. **Retention proves value** — clients keep coming back because the product is great.
4. **Best UX = no thinking** — users get everything they need to integrate AI into any business without cognitive load. Our clients want what we want: revenue, margin, and real help for *their* clients.
5. **Exception**: we may forget margin temporarily (Amazon-style) only with cash flow or investors backing the vision — explicit, time-boxed, never accidental.

## How cycles measure it (inputs via web, not code)

- `/admin.html` → Metrics: `revenue`, `ai_cost`, `infra_cost`, `niche_avg_margin` per period.
- `GET /api/metrics` returns last entry + computed `margin = (revenue - ai_cost - infra_cost) / revenue`.
- Board `/` shows the margin strip: margin vs niche average. Green only when above.
- Costs include AI: every leg should push `ai_cost` honestly — hiding inference spend is lying about margin.

## Current targets (editable in Admin → Config)

- `margin_target`: 0.40 (40%)
- `niche_avg`: 0.25, `niche_stdev`: 0.05 → stretch goal = avg + 2 stdevs = 0.35
- `domain_budget_yearly`: 20 (USD, owner cap)
