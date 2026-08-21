# e037 — AI Education Video: 7-Day Challenge

**Goal**: render Stage 4 of e032 — the teaching video for the 7-day challenge "Tu primer video explicativo en 7 días" (ag-06 + ag-07). Faceless explainer, Spanish narration, no facecam.

**Sources of truth (verbatim, no invention)**:
- Script: `../e032-ai-skills-digest/ag-07-engine/output/episode-1-script.md` (13 scenes, ~6:45, hook → 7 days → honesty note)
- Challenge: `../e032-ai-skills-digest/ag-06-engine/output/episode-1-challenge.md`
- Costs/honesty: `../e032-ai-skills-digest/ag-05-synthesis/output/teaching-plan.md` + `synthesis.md` + `profit-plan.md`
- Pipeline precedent: `../e029-html-video-explainer/videos/phone-ai-developer/` (58s, 1920x1080, Deepgram Aura-2 aura-2-celeste-es + Nova-3 captions, Capsule preset)
- Delivery: `videos/7-day-challenge/renders/video.mp4` (16:9 primary, 9:16 cut)

**Rules**:
- One Spanish voice throughout (Deepgram Aura-2 aura-2-celeste-es or KIE Gemini TTS Alnilam/Gacrux/Puck/Sulafat/Umbriel/Vindemiatrix) — consistent.
- Costs tagged [measured]/[estimated] exactly as teaching-plan; OPEN GAP for phone-only assembly stays honest.
- Honesty footer verbatim: "Pasado no es futuro" + prices measured 2026-08-18.
- Captions mandatory: word-timed via Deepgram Nova-3 before captions.mjs build.
- Cloud-first (e032 Rule 1), measurement-based timeouts (Rule 2).

**Pipeline**:
```
SCRIPT.md (ag-07 verbatim) -> TTS (bin/dg-tts.sh Aura-2) -> STT (bin/dg-transcribe.sh Nova-3) -> audio_meta.json -> captions.mjs build -> HyperFrames check -> render
```

**Agent**: ag-01 — the video builder (HyperFrames).
