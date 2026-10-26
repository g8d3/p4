# Sales page audit — echolike.app, phone size (q13)

- When: 2026-10-25 17:20–17:25 Bogotá (UTC-5)
- Pages: `https://echolike.app/` (EN), `https://echolike.app/es/` (ES)
- Viewport: 390 × 844 CSS px, DPR 2 (headless Chromium); screenshots saved from the same viewport
- Read-only: no forms submitted, nothing posted/pushed/deployed
- Evidence: live DOM geometry + visible text via OpenBot browser; phone screenshots via the repo's headless check (`tests/verificar_vivo_movil.py`, 25/25 pass)
- Caveat: Rayo's model cannot view images, so the screenshots below are for human review; pass/fail is based on measured positions and page text, not on eyeballing the PNGs.

## Verdict: 4 pass, 2 fail

| # | Gap (NEXT.md) | EN | ES | Smallest concrete fix |
|---|---|---|---|---|
| 1 | Price | ✓ PASS | ✓ PASS | None required. Optional: lift the muted 13.6px price line under the CTA to ≥16px and add a "Join Pro waitlist" mailto (overlaps q9). |
| 2 | Clear CTA | ✓ PASS | ✓ PASS | None. |
| 3 | Proof without jargon | — FAIL | — FAIL | Cut the Directory and Alerts cards from the sales page; keep only the Extension proof and state one buyer outcome. |
| 4 | Why us | ✓ PASS | ✓ PASS | None. |
| 5 | Steps + FAQ | ✓ PASS | ✓ PASS | None. |
| 6 | Nav not pulling buyers away | — FAIL | — FAIL | Hide the fixed bottom tab bar on `/` and `/es/` only (keep it on product pages); header and footer links still navigate. |

### Measured facts behind the table

- CTA: green `#0d6b3c`, 52px tall, 241px (EN) / 292px (ES) wide, top at y=366 (EN) / y=459 (ES) — above the 844px fold, links to `/extension/` (`/es/extension/`). Button text: "Get the extension — free" / "Conseguir la extensión — gratis".
- Price: "Pro plan, coming soon: $5/mo billed yearly ($60/yr). Founder tier: $39 one-time for the first 100 buyers." at y=434 (EN) / y=527 (ES), 13.6px, muted grey `#6e685b`. Present and readable, but secondary and not actionable.
- No horizontal overflow (scrollWidth 375 ≤ viewport 390); no console errors; both pages 200.
- Sections exist in order: Why → What the loop has done → How it works → FAQ → The loop behind it → Talk to us → Ready when you are.
- Fixed bottom tab bar: `nav.tabbar`, position fixed, 58px tall, always visible over content; links Products / Loop / Progress / Account (ES: Productos / Loop / Progreso / Cuenta). None points at the offer.

## Gap detail

### 1. Price — PASS
The decided price is on both pages, directly under the primary CTA, including the yearly total and the founder tier. Missing only a way to act on it: "coming soon" and no buy/waitlist link. That is the separate q9 job, so not counted against this gap.

### 2. Clear CTA — PASS
One dominant, above-the-fold button on both languages, consistent label, single destination. No competing coloured button above the fold.

### 3. Proof without jargon — FAIL
The section is titled "What the loop has done" / "Lo que ha hecho el bucle" and proves the business, not the buyer's outcome:
- "751 posts from X" (relevant, sourced, matches the 751 lines in `estado/likes_extension.jsonl` today)
- "27 entries in 4 tables" (the Directory — irrelevant to someone buying an X likes tool)
- "559 tracked markets" / "18 of 20 exchanges read" (funding alerts — unrelated product, and "funding", "exchanges", "markets" are jargon for this buyer)

No customer quote, example output, or before/after, and nothing on the page says what the buyer gets in their first week. Smallest fix: on the sales page keep the Extension card only, reframe it as "751 posts saved from X, grouped by topic" plus one concrete outcome line; move Directory/Alerts proof to their own pages.

### 4. Why us — PASS
Three specific reasons with no jargon: data stays in the browser, no account/tracking, install in minutes, works where the buyer already is (X). Clear enough to answer "why this instead of a read-later app".

### 5. Steps + FAQ — PASS
Three numbered steps (install → like/bookmark on X → see grouped data) and four FAQs (price, data location, browsers, uninstall), all visible on phone.

### 6. Bottom nav — FAIL
The `.tabbar` is fixed at the bottom of every phone viewport (y=786, 58px) with four exits: Products, Loop, Progress, Account. On the sales page this sits under the CTA the whole time and offers no path to the offer, so it competes with the single action the page wants. Smallest fix: one scoped rule, e.g. `.tabbar{display:none}` on the sales page template only; the sticky header (logo, Refresh, ES) and footer links remain.

## Spanish: reads machine-translated (understandable, but calques)

Native-quality issues found in the live `/es/` copy, worst first:

| Live ES text | Problem | Suggested |
|---|---|---|
| "operada por un **bucle** de agentes de IA" | "loop" translated literally; body says "bucle", nav says "Loop" | "llevada por un **ciclo** de agentes de IA" (and nav "Ciclo") |
| "cada tarea que **corre el bucle**" | run-the-loop calque | "cada tarea que **ejecuta el ciclo**" |
| "**Nivel fundador**: $39 pago único" | "founder tier" literal | "**Oferta fundador**" or "**Plan fundador**" |
| "$5/mes **facturado anual**" | "billed yearly" calque | "$5/mes **con pago anual**" |
| "con notas y **siguientes pasos**" | "next steps" calque | "con notas y **próximos pasos**" |
| "cuándo corrió y **cuándo sigue**" | wrong/ambiguous ("when it follows") | "cuándo corrió y **cuándo vuelve a correr**" |
| "57 tareas **corridas** por 5 agentes" | "run" calque | "57 tareas **ejecutadas** por 5 agentes" |
| "559 mercados **seguidos**" | "tracked" literal | "559 mercados **monitoreados**" |
| "18 de 20 exchanges **leídos**" | "read" calque | "18 de 20 exchanges **consultados**" |
| "**Lista** cuando tú lo estés" | "Ready when you are" literal + wrong gender | "**Listo cuando quieras**" |
| "comparados **lado a lado**" | "side by side" anglicism | "comparados **entre sí**" |
| "No es asesoría financiera. Nada de esto es asesoría de inversión." | literal repetition of two EN sentences | "No es asesoría financiera ni de inversión." |
| "lo que guardas o **te gusta** en X" | "you like" ambiguous | "lo que guardas o **marcas con Me gusta** en X" |

Overall: a Spanish speaker understands the page, but these strings read translated rather than written. Fixing the ten above (one copy pass, EN unchanged) would remove the machine-translated tell.

## Phone screenshots (390×844)

EN
- Gap 1–2 (price + CTA): `/home/vuos/code/p4/e092-echolike/reportes/q13_20261025_en_1price.png`, `.../q13_20261025_en_2cta.png`
- Gap 3 (proof): `.../q13_20261025_en_3proof.png`
- Gap 4 (why): `.../q13_20261025_en_4why.png`
- Gap 5 (steps, FAQ): `.../q13_20261025_en_5steps.png`, `.../q13_20261025_en_6faq.png`
- Gap 6 (nav/tab bar): `.../q13_20261025_en_7nav.png`

ES
- Gap 1–2: `/home/vuos/code/p4/e092-echolike/reportes/q13_20261025_es_1price.png`, `.../q13_20261025_es_2cta.png`
- Gap 3: `.../q13_20261025_es_3proof.png`
- Gap 4: `.../q13_20261025_es_4why.png`
- Gap 5: `.../q13_20261025_es_5steps.png`, `.../q13_20261025_es_6faq.png`
- Gap 6: `.../q13_20261025_es_7nav.png`

Baseline full-page-top shots from the repo check: `reportes/vivo_movil_en_20261025_1720.png`, `reportes/vivo_movil_es_20261025_1720.png`.

## Not in scope
- No checkout/waitlist was added (q9), no publish or commit of site code.
- Directory and funding pages were not audited.
