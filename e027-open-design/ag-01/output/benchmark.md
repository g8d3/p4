# e027 Open Design — benchmark: where does it fit in p4?

Date: 2026-08-15. Author: ag-01. Evidence: real commands + measured outputs
from this session (see `exploration.md` for setup and pitfalls).

## Verdict (TL;DR)

**Adopt as a design/artifact front-end, keep p4's video pipeline for final encodes.**

Open Design is the strongest "HTML as source of truth" design engine we have
tested for coding agents. It is NOT a competitor to p4's KIE image/video models —
it is a *generation and capture source* that feeds the same downstream pipeline
(generated HTML → headless Chrome → ffmpeg/VAAPI). It should be **adopted** for
landings, decks, dashboards, and HyperFrames motion graphics; **ignored** as a
final-encode path (its renderer emits libx264, not VAAPI) and NOT a replacement
for KIE generative models (image/video generation still needs provider keys).

## Measured evidence (this session)

### Setup cost
- `git clone --depth 1` + `pnpm install` (1m32s) + `pnpm --filter @open-design/daemon build` + `pnpm tools-dev start web` — all local, ~5 minutes total, no API keys required for the HTML/video path.
- Node 24 + corepack-pinned pnpm 10.33.2. Daemon on :7457, web on :5173, both verified (`/api/health` → `{"ok":true}`; web HTTP 200).

### Artifact 1 — landing page (`open-design-landing` skill, "default" DS)
- Via `POST /api/runs` → daemon spawned `opencode run --format json`, staged skill to project `.od-skills/`, agent filled `inputs.json` (p4 Lab brand), copied 16 collage assets, ran the deterministic composer.
- Output: `index.html` **98 KB**, 8× "p4 Lab" content hits.
- Verification: headless Chrome screenshot at 1440×900 → 42% non-white pixels, 242 unique gray levels (real page, not a stub). Page renders fully.

### Artifact 2 — video (`hyperframes` skill, HyperFrames HTML→mp4)
- Agent scaffolded a HyperFrames composition (`.hyperframes-cache/<id>/`: hyperframes.json + meta.json + index.html), authored content about Open Design, ran `npx hyperframes lint` / `check` (fixed contrast warnings), then dispatched `od media generate --surface video --model hyperframes-html --composition-dir ...`.
- Render: 21.5 s elapsed, output **open-design-intro.mp4** = 16.0 s, 1920×1080, h264, 30 fps, 1.29 MB.
- Verification: ffprobe (real h264 stream), 4 frames extracted + OCR → real text ("Open Design", "One engine. Every artifact.", capabilities, CTA, URLs). Not blank, not a stub.
- Total wall time for the run: 13.5 min (agent composition/QA dominated; render itself 21 s).
- No generative video model used — pure HTML → Chrome frames → mp4.

### Design-system propagation (DESIGN.md) — CONFIRMED
- Created `user:ag01-brutal` (black bg #000 / neon accent #00FF00 / Courier Mono / 0px radius / 2px white borders), a sharp contrast to the "default" Neutral Modern DS.
- Daemon rescans user DS dir per request → appears as `published` (needed `metadata.json` with `"status":"published"`; drafts are rejected by projects).
- Rendered the SAME landing skill (`open-design-landing`) against the brutal DS:
  - Artifact `landing-brutal.html` (95 KB) contains the tokens: `#000000` background, `#00FF00`/`#0f0` accent (×2), Courier Mono (×4).
  - Headless Chrome screenshot: **96% non-white pixels** (vs 42% for the neutral default) — the black brutal background dominates; OCR confirms readable p4 Lab content.
- **Conclusion: DESIGN.md tokens propagate end-to-end** into generated artifacts via the composed system prompt + `tokens.css` binding.

## Where Open Design fits in p4

| p4 need | OD capability | Verdict |
|---|---|---|
| HTML capture source for videos | HyperFrames HTML→mp4; frames ARE the video | **Adopt** — deterministic, no video model needed, quality is design-encoded |
| Brand consistency | DESIGN.md + tokens.css as the brand contract; craft references | **Adopt** — a portable brand source p4 videos/slides/landings can share |
| Decks / landings / dashboards | deck/prototype/template modes → single-file HTML | **Adopt** — faster than hand-building; design-quality baseline |
| HyperFrames vs e018 | OD uses `npx hyperframes` (heygen-com/hyperframes compatible), same framework e018 uses | **Align** — same authoring; OD automates the loop |
| Final video encode | emits libx264 (Lavc60) | **Ignored** — p4 rule: final encodes MUST be h264_vaapi. Re-encode OD's mp4 with `encode_vaapi.sh`. |
| KIE image pipeline | OD media surfaces call provider models (needs keys); deterministic HTML needs none | **Complement** — OD for structure/typography/video-frames; KIE for generative imagery |

### Comparison vs p4's existing headless-Chrome slides path
- p4 slides path: agent writes HTML slides → headless Chrome `--screenshot` per slide → PNG → ffmpeg. Manual per-slide.
- OD deck/prototype: agent writes one self-contained `index.html` with in-page navigation + deterministic composer. The HyperFrames path automates the *animation+timing* part that p4 currently scripts by hand.
- Both feed the same capture pipeline; OD removes the "write HTML + drive Chrome manually" work.

### Costs
- HTML/video/HyperFrames path: **$0 model cost** (only the local agent CLI tokens; measured: video run ~81k input + 16k output tokens on opencode-go).
- Agent time dominates: 5–30 min per run by design (QA, contrast audits, content authoring). For time-critical p4 production, pre-fill inputs/briefs and use narrow prompts ("do not ask questions; produce the artifact").

## Recommendation

1. Add a p4 `DESIGN.md` brand system into `.od/design-systems/` and point all OD-driven landings/decks at it.
2. Use `hyperframes-html` as an HTML-capture source for p4 videos; always re-encode the mp4 with `encode_vaapi.sh` before final delivery.
3. Keep KIE for generative imagery (storyboard/character sheets); OD for interface/text/motion artifacts.
4. Do NOT rely on the web UI for headless automation — the CLI/API path (`project create` + `/api/runs`) works fully.
