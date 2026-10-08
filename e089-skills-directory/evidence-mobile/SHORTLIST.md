# Mobile-web-design skills — shortlist (2026-10-08)

Research via tinyfish search + fetch. Raw evidence: one .md per source in this folder (`evidence-mobile/`).
Every claim below links to its evidence file. Numbers are page-shown values at fetch time, not endorsements
(repo stars are shared across whole collections unless noted).

## Recommended 5 (distinct angles, one render each)

| # | Skill | Install | skills.sh | Emphasis | Popularity |
|---|-------|---------|-----------|----------|------------|
| 1 | `responsive-design` — wshobson/agents | skills.sh panel / `wshobson/agents` | [page](./03-skills-sh-wshobson-responsive-design.md) | Modern CSS engine: container queries, fluid type/spacing via `clamp()`, Grid, content-based breakpoints | 20.0K installs — highest of all candidates; 40.3K repo stars (shared) |
| 2 | `responsive-design` — supercent-io/skills-template | skills.sh panel / `supercent-io/skills-template` | [page](./04-skills-sh-supercent-responsive-design.md) | Classic mobile-first ladder 320px→1440px+, Flexbox/Grid, responsive images (`srcset`/`<picture>`), relative units | 11.2K installs; 88 repo stars |
| 3 | `mobile-ux-optimizer` — curiositech/some_claude_skills | skills.sh panel / `curiositech/some_claude_skills` | [page](./02-skills-sh-mobile-ux-optimizer.md) | Only truly mobile-UX-scoped: viewport/`100vh`/safe-area, touch targets, bottom nav, gestures, mobile perf | 489 installs; 242 repo stars (shared) |
| 4 | `responsive-craft` — kylezantos (GitHub only) | clone repo / copy skill folder | n/a (not on skills.sh) — [evidence](./06-github-responsive-craft.md) | Workflow + tooling: audit/build/preview modes, multi-breakpoint preview (375/768/1024/1440), 8 "design fork" patterns (tables, sidebars, bento) | 61 stars / 3 forks, skill-specific (dedicated repo) |
| 5 | `mobile-first-design` — aj-geddes/useful-ai-prompts | `npx add-skill https://github.com/aj-geddes/useful-ai-prompts/tree/main/skills/mobile-first-design` | n/a (directory listings, not skills.sh) — [evidence](./07-eliteai-mobile-first-design.md) | Progressive-enhancement ladder (mobile 320–480 → tablet → desktop) + `references/` on responsive impl, mobile perf, 44px touch targets | No per-skill installs published (stated gap) |

## Why these 5

- **No overlap:** modern-CSS (1) vs classic-breakpoints+images (2) vs touch/viewport UX (3) vs audit-and-preview workflow (4) vs progressive-enhancement teaching ladder (5). Each should visibly change the same site's render.
- **Popularity-ordered where measurable:** 1 and 2 lead by installs; 3 is the only mobile-dedicated skill on skills.sh; 4 and 5 trade raw numbers for distinctive mechanics (preview scripts, perf references).
- **Factual gaps flagged, not filled:** 5 has no published install count; 4 has no skills.sh presence; repo star counts for 1–3 cover whole collections ([context](./10-skillselion-frontend-top10-context.md)).

## Considered, not picked

- `responsive-design` — owl-listener/designer-skills (2.0K installs): solid but overlaps 1+2; best alternate ([evidence](./01-skills-sh-owl-listener-responsive-design.md)).
- `responsive-design` — planetabhi/skills (57 installs, newest Sep 2026): principled content-first rules, but thinnest adoption ([evidence](./05-skills-sh-planetabhi-responsive-design.md)).
- `design-mobile-apps` — sleekdotdesign: native-app API skill (needs `SLEEK_API_KEY`), wrong domain ([evidence](./08-github-sleek-design-mobile-apps-excluded.md)).
- `nextjs-shadcn-builder` — ovachiever: mobile-first is one incidental bullet in a framework-migration tool ([evidence](./09-skills-sh-nextjs-shadcn-builder-excluded.md)).

## Method note

Mechanism behind all candidates (SKILL.md packs, ~100 tokens idle, portable across Claude Code/Codex/Cursor): [context](./11-context-bitdoze-kimi.md).
