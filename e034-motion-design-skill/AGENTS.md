# e034 — Motion Design Skill playground

Playground for [**LottieFiles/motion-design-skill**](https://github.com/LottieFiles/motion-design-skill)
— a philosophy-first, implementation-agnostic motion design skill for AI agents:
"think like a motion director — pick timing, easing, and choreography before writing animation code."

Scope: **install the skill, then prove it on production output** — 5 short HyperFrames
motion graphics, each demonstrating one of the skill's concepts, rendered to GPU-encoded MP4.

## Verified findings (2026-08-19)

| Claim | Verdict | Evidence |
|---|---|---|
| Skill is a self-contained MIT package (`npx skills add`) | ✅ | 80K, clean structure: `SKILL.md` + `director/` + `patterns/` + `reference/` |
| The 8-step checklist + personality table maps directly onto HyperFrames authoring | ✅ | Each composition below was authored start-to-finish from its row (duration/easing/overshoot) |
| The skill is implementation-agnostic | ✅ | Every concept translated to GSAP tweens inside the HyperFrames timeline contract — zero conflict |

### What the skill actually changed about the work

- **Durations came from tables, not taste**: Playful 150/250/400ms, Premium 350/500/800ms,
  Corporate 200/300/450ms, Energetic 100/180/300ms (quick/standard/slow)
  — plus element-type durations (card 200-350ms, dramatic reveal 600-1200ms, error shake
  300-400ms).
- **Easing is directional**: entrance = ease-out family, exit = ease-in, on-screen =
  ease-in-out, looping ambient = sine. Overshoot budget per personality (Playful 10-20%,
  Premium 0%, Corporate 0-3%, Energetic 15-30%).
- **Three motion layers, always**: primary (the hero action) + secondary (shadows, sub-elements
  arriving after the hero) + ambient (breathing orbs, drifting blobs, subtle pulses) —
  this was the single biggest quality lift vs a "one tween per element" default.
- **Not obeyed blindly**: the skill's Micro cascade/Standard/Dramatic stagger budgets all stay
  under the skill's own 500ms rule; the "never opacity-only" rule pushed the corporate bars and
  progress fills onto `scale` (transform) instead of opacity.
- **Skill gaps discovered**: it has no guidance on the hyperframes determinism contract
  (no `Date.now()`, no infinite loops, single paused timeline) — that compatibility layer is
  exactly what `/hyperframes-core` adds. The two skills are complementary, not competing.

## The animations (rendered, GPU-encoded)

| File | Concept | Skill reference | Duration |
|---|---|---|---|
| `output/reel.mp4` | **Full demo reel** — title + all 5 animations concatenated (h264_vaapi) | — | 42.0s |
| `output/playful-card.mp4` | Card entrance, personality Playful | 8-step checklist, Disney squash & stretch, back.out overshoot | 6.5s |
| `output/premium-reveal.mp4` | Typographic reveal, personality Premium | Dramatic reveal, zero overshoot, golden hairlines | 8.0s |
| `output/corporate-dashboard.mp4` | Dashboard load, personality Corporate | Wave stagger, snappy 0.2,0,0,1 curve, linear progress | 7.0s |
| `output/energetic-hero.mp4` | Hero slam + streaks, personality Energetic | expo.out, per-letter stagger, counter-motion, pulse rings | 5.5s |
| `output/state-feedback.mp4` | Loading → success → error states | Patterns: state-feedback (scale pop, check draw, error shake, toasts) | 7.0s |

All 5 pass `hyperframes check` with **0 errors, 0 warnings** (lint, runtime, layout, motion,
contrast). A few decorative off-canvas infos are intentional (orbs/streaks bleeding past the
frame, marked `data-layout-allow-overflow`).

## Layout

| Path | What |
|---|---|
| `upstream/` | The motion-design-skill source (MIT, cloned + `.git` stripped, 80K — committed) |
| `animations/` | HyperFrames project (pinned `hyperframes@0.8.2`, scaffolded with `init --example blank`) |
| `animations/compositions/*.html` | The 5 standalone compositions |
| `animations/renders/` | Raw browser renders from `hyperframes render` (libx264 — gitignored) |
| `output/*.mp4` | Final deliverables, re-encoded with `encode_vaapi.sh` to **h264_vaapi** (gitignored) |

## Reproducing

```bash
# 1. Validate one (or all) composition:
cd animations
cp compositions/playful-card.html index.html && npm run check   # check runs the project's index.html

# 2. Render a specific composition:
npx --yes hyperframes@0.8.2 render -c compositions/playful-card.html -o renders/playful-card.mp4

# 3. Final GPU encode (p4 rule — FINAL videos must be h264_vaapi):
bash ../e023-build-in-public/bin/encode_vaapi.sh animations/renders/playful-card.mp4 output/playful-card.mp4
```

## How the skill was wired into authorship

1. Read `upstream/.../SKILL.md` + `reference/timing-easing-tables.md` for the curves/tables.
2. Read `/hyperframes-core` + `/hyperframes-animation` for the render contract.
3. Wrote each composition start-to-finish from the personality's row, then ran `hyperframes check`
   per file (`cp` it into `index.html`, check, fix, iterate) until 0 errors/0 warnings.
4. Rendered each with `-c compositions/<name>.html`, verified frames differ across time and
   nothing is black, then re-encoded to `h264_vaapi`.

## Caveats

- `check` lints the project's `index.html` only — there is no `-c` flag on check/lint. Validating
  N compositions means swapping each file into `index.html` and re-running. Run them serially;
  each spawns a Chrome instance.
- Contrast (WCAG) is the strictest gate: light-on-light microtext fails hard. The skill says
  nothing about accessibility — that gap is on HyperFrames' checker, not the skill.
- Final videos are silent by design (motion graphics, no narration — `/motion-graphics` route).

## Session trail

Recorded 2026-08-19. See `e000-fundamentals/trail.md`.

### Demo reel (user request, same session)

User asked to join everything into one demonstrative video. Rendered the title card
(`animations/renders/title.mp4`, the project's `index.html`), then concatenated
title + 5 animations with the ffmpeg concat demuxer (`-c copy`) and re-encoded the
result through `encode_vaapi.sh` → `output/reel.mp4` (42s, 1920×1080, 30 fps, h264_vaapi).
Frame checks confirm the reel plays (no black segments).