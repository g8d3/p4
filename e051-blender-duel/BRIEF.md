# BRIEF — improved instruction for the talking-duo comparison

## Your original idea (kept)

> Two simple experiments: one with a widely known procedural generator, one
> from scratch. Same simple scene, two characters talking. Cover as much of
> the 3D pipeline as possible. Measure which way is more efficient.

## What "talking" actually means (you were right to ask)

"Talking" is never one thing. It is 4 layers, cheapest first:

1. **Jaw flap** (minimum viable talking): jaw opens/closes in rhythm.
   Alone it reads as "talking" at 3+ meters distance.
2. **Head + hands** (what you guessed): listener nods, speaker bobs head and
   waves one hand. This sells 80% of the shot.
3. **Lip-sync visemes** (mouth shapes for B/M/P, E, O, ...): needed only in
   close-up. 10x the work of layer 1.
4. **Face** (blink, eyebrows, cheeks): polish, skip for a speed test.

**This duel tests layers 1+2 only.** That is the correct scope for a first
comparison: minutes per track instead of hours, and the rig/anim difference
still shows clearly.

## The full 3D pipeline (you named 3 of 8)

1. **Modeling** — build the bodies. (Frozen here: capsules in both tracks.)
2. **UV + Texturing/Shading** — flat colors only, no UVs (fastest).
3. **Rigging** — armature + parenting + weights. THIS is compared.
4. **Animation** — jaw/head/hands keyframes. THIS is compared.
5. **Lighting + Camera** — frozen (same sun, fill, camera).
6. **Rendering** — frozen (same EEVEE settings).
7. **Sound + Subtitles** — skipped (fake silent dialogue; add TTS later).
8. **Composite/Edit** — side-by-side concat of the two mp4s (1 ffmpeg line).

## How efficiency is measured

- **Build time**: wall-clock of each script (model / rig / anim split).
- **Authoring cost**: lines of rig+anim code, number of hand-placed keyframes.
- **Render time + file size**: identical settings, so any delta = rig cost.
- **Quality rubric (1-5, judged on stills)**: silhouette, talking readability,
  gesture variety, intersection/deformation artifacts.

## Fairness rules

- Same characters, same camera, same lights, same render settings.
- Same dialogue timing (A: 1-72, B: 73-144).
- Only rig source (Rigify meta-rig vs custom bones) and animation source
  (computed sine loop vs hand-authored acting) may differ.
