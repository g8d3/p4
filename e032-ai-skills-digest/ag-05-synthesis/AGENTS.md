# ag-05 — Synthesis: what to teach, how to profit

Stage 2 of e032. You consume the four Stage-1 research reports and produce ONE
synthesis document that turns them into a decision-ready **teaching plan +
monetization plan**. The user's locked goal (2026-08-18):

> **Teach first, monetize later.** Teachable content for a NON-TECHNICAL
> Spanish-speaking audience. Profit later via digital products (primary),
> audience/ads (channel), maybe client services.

## Inherits
- [../../AGENTS.md](../../AGENTS.md) — experiment scope, Stage 2 contract
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md) — principles, data formats (CSV preferred), quiet-mode caps

## Inputs (read all four, do not re-download or re-research)

| Agent | File | What it covers |
|---|---|---|
| ag-01-video | `../ag-01-video/output/skills-video.md` + `recommendations.md` | video/content creation skills, cloud providers, prices |
| ag-02-products | `../ag-02-products/output/skills-products.md` + `recommendations.md` | digital product creation skills |
| ag-03-marketing | `../ag-03-marketing/output/skills-marketing.md` + `recommendations.md` | marketing/selling/acquisition skills |
| ag-04-crypto | `../ag-04-crypto/output/skills-trading.md` + `recommendations.md` | crypto: VERDICT = DROP (method as case study only) |

## Your deliverables (in `output/`, one file per deliverable)

### 1. `output/synthesis.md` — the single source of truth (~2-4 pages)
Structure:
- **The landscape**: one table of the top teachable skills across video +
  products + marketing, with their cloud cost (monthly), skill level needed,
  and difficulty. Cross-domain synergies (e.g. "video → product → funnel")
  called out as rows.
- **What a beginner can actually ship today** (non-technical, phone-based if
  possible): 3 concrete teaching tracks, each = one complete "from zero to
  shipped" journey. Ranked by teachability × profitability.
- **Crypto**: one short paragraph honoring the DROP verdict — what to keep
  (the critical-thinking method: fees filter, OOS testing) as a story/case
  study, nothing that promises returns.
- **Gaps**: what the research did NOT cover that a teaching plan would need.

### 2. `output/teaching-plan.md` — what we will teach (concrete)
- Audience: non-technical, Spanish-speaking, phone + cheap AI subs.
- 3 tracks, each: name, learner outcome, 4-6 modules, rough hours to teach,
  cloud stack cost for the student, deliverable the student builds.
- The FREE hook (to build audience) and the PAID product (to monetize later).
- Keep it honest: mark every cost as measured/estimated, cite the source report.

### 3. `output/profit-plan.md` — how the teaching becomes income (later)
- Product ladder: free content → low-ticket (guide/template) → mid (course) →
  high (service/coaching or done-for-you). Numbers from the reports, not vibes.
- Channel: YouTube/IG/TikTok repurposing loop (ag-01 + ag-03 outputs).
- What is NOT worth monetizing (per the reports' own honesty).

### 4. `output/done.txt` — headline synthesis + verdict in one line.

## Cadence
- Agent id: `ag-05-synthesis`. Heartbeat every milestone:
  `e000-fundamentals/bin/progress-monitor/report.sh ag-05-synthesis "<step>"`.
- Expected interval while working: 60s; you are inside the quiet cap (1.5
  cores/8 GiB) — work in single steps, background everything.

## Rules
- Read-only on the inputs. Write ONLY to your `output/`.
- No new web research — the four reports are the evidence. If something is
  missing, mark it as a GAP, don't invent it.
- 60 min deadline: stop, ship partial, notify.
- Every command timed + backgrounded + self-wake (measurement-based timeouts).

## Notify
- On finish: `notify.sh done "ag-05 synthesis finished: <headline>"`.
- On failure: `notify.sh error "ag-05 failed: <cause>"`.

## Self-command
- Background everything: `> /dev/null 2>&1 &`
- Self-wake: `(sleep <mean+4σ>; tmux send-keys -t 32-5 "Self-wake: step=N, check" Enter) &`