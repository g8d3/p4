# ag-12-pilot — The data-viz content pilot

Fresh attempt at attention-grabbing content. The engine agents (ag-06..11)
produced correct-but-flat text ("7-day challenge" guides, generic hooks). The
user's verdict: nothing in the produced files calls attention for social media.

**The thesis this agent proves**: the research reports (ag-01..04) already
contain the value — verified numbers, measured prices, honest failures. The
missing piece was **packaging**: data-viz content built in code (SVG/HTML)
instead of AI-generated images (where agents fail on aesthetics), plus hooks
that lead with numbers, not promises.

## Deliverable

The pilot shipped as two artifacts:

1. `piloto.html` — "El negocio digital con agentes de IA: la factura real".
  A self-contained, mobile-first page with 7 numeric charts (100× SEO cost
  drop, the $0 SaaS stack, <$1/video breakdown, what NOT to sell, 9-of-10
  strategies dying to fees, the revenue ladder, the YouTube Feb-2027 deadline)
  and 5 ready-to-post hooks, one per platform.
2. `videos/factura-real-ia/renders/video.mp4` — a 52s 9:16 Short (faceless
  explainer, bold-poster data-viz in code) narrating the strongest figures in
  a cascade: the 100× cost drop, the $0 SaaS stack, <$1/video, the 9-of-10
  honesty turn, the $100-500 service, the Feb-2027 YouTube deadline. GPU
  encode (h264_vaapi). Voice: Kokoro `ef_dora` (es). No captions (offline
  Kokoro has no word timestamps).

## Inherits
- [../../AGENTS.md](../../AGENTS.md) — experiment scope, always-on engine
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md) — conventions, data formats, honesty rules
- [../ag-01-video/output/recommendations.md](../ag-01-video/output/recommendations.md) — the verified video numbers
- [../ag-02-products/output/recommendations.md](../ag-02-products/output/recommendations.md) — the $0 product stack
- [../ag-03-marketing/output/recommendations.md](../ag-03-marketing/output/recommendations.md) — the 100× SEO + email ROI numbers
- [../ag-04-crypto/output/done.txt](../ag-04-crypto/output/done.txt) — the 9-of-10 fees verdict
- [../ag-05-synthesis/output/profit-plan.md](../ag-05-synthesis/output/profit-plan.md) — the revenue ladder

## Rules
- Every number must trace to a report with a source tag (`ag-0N`). No new web
  research; the reports are the evidence.
- Honesty rule applies: measured vs verified vs estimated are distinguished;
  past ≠ future is stated.
- If the pilot is approved, this agent's successor is the full content cycle:
  long article + carousel + thread + Short reusing these charts.

## Cadence
- Agent id: `ag-12-pilot`. Report via
  `e000-fundamentals/bin/progress-monitor/report.sh ag-12-pilot "<step>"`.
- This is a design/content agent: start at long-step N=300, not booting-30.
