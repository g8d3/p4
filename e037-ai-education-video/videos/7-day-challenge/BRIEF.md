---
workflow: faceless-explainer
flow: automation
storyboard: no
mode: autonomous
message: "Sin cámara. Sin cara. Sin saber editar. En 7 días publicas tu primer video explicativo con IA, desde el teléfono."
destination: youtube
aspect: 1920x1080
language: es
audience: no-technical
length: 405s
angle: how-to
---

## Intent

Faceless explainer for Stage 4 of e032 — the teaching video for the 7-day challenge "Tu primer video explicativo en 7 días" (ag-06 + ag-07). Spanish narration, no facecam, typography + icons + abstract visuals only. Message: en 7 días, con 20-30 min/día y tu teléfono, pasas de una idea a un video publicado con voz, imágenes y subtítulos de IA por $0-1. Costs tagged [measured]/[estimated] verbatim from teaching-plan; OPEN GAP for phone-only assembly stays honest; honesty footer "Pasado no es futuro" verbatim.

Sources: `../../e032-ai-skills-digest/ag-07-engine/output/episode-1-script.md` (13 scenes, ~6:45), `../../e032-ai-skills-digest/ag-06-engine/output/episode-1-challenge.md`, `../../e032-ai-skills-digest/ag-05-synthesis/output/teaching-plan.md` + `synthesis.md` + `profit-plan.md`. Pipeline precedent: `../../e029-html-video-explainer/videos/phone-ai-developer/` (58s, 1920x1080, Deepgram Aura-2 aura-2-celeste-es + Nova-3 captions, Capsule preset).

## Customizations

- Capsule preset (cream / ink pills, Bodoni Moda + Space Grotesk, candy pastels, grain + radial glows) — same as e029 for warm non-technical feel.
- One Spanish voice throughout: Deepgram Aura-2 aura-2-celeste-es (primary) or KIE Gemini TTS Alnilam/Gacrux/Puck/Sulafat/Umbriel/Vindemiatrix — consistent across all 13 scenes.
- Captions mandatory: word-timed via Deepgram Nova-3 before captions.mjs build.
- Costs rendered as chips with [measured]/[estimated] tags; Day 4 "OPEN GAP" shown as yellow badge, not hidden.
- Honesty card verbatim at 5:50-6:20.

## Notes

- Narration and on-screen text: Spanish (es). Code/commits: English.
- Aspect primary 1920x1080 (16:9); 9:16 Short cut is reposition-only, same audio.
- Delivery: `renders/video.mp4` — HyperFrames HTML→MP4 via `bin/dg-tts.sh` Aura-2 → `bin/dg-transcribe.sh` Nova-3 → audio_meta.json → captions.mjs → check → render.
- Cloud-first (e032 Rule 1), measurement-based timeouts (Rule 2).
