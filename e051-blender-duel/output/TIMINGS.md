# e051 results — procedural (Rigify) vs from-scratch (custom rig), same 6 s shot

## Machine timings (wall-clock, Blender 4.0.2 headless, EEVEE 640x360)

| Stage | Track A procedural | Track B from scratch |
|---|---|---|
| Model (primitives) | 0.0 s | 0.0 s |
| Rig (parent + weights) | 0.6 s (2x 159-bone meta-rigs) | 0.1 s (2x 5-bone custom) |
| Animation (keyframes) | 0.1 s (~320 computed keys) | 0.0 s (~88 hand-placed keys) |
| Render 144 f EEVEE | 8.1 s | 8.0 s |
| **Total script** | **8.8 s** | **8.2 s** |

Compute time is noise — both build in <10 s. The real cost is AUTHOR time:
A ≈ 15 min (incl. one API bug), B ≈ 25 min (incl. three beginner bugs).
**Procedural ≈ 2x faster to author for this shot.**

## Output sizes

| File | Track A | Track B | Track C (MB-Lab) | Track F (web) |
|---|---|---|---|---|
| .blend | 2.28 MB (heavy rigs) | 1.54 MB | 52 MB (2x 17k humans + 83 shape keys) | n/a |
| .mp4 (6 s, 640x360) | 131 KB | 111 KB | 102 KB | n/a (live render) |
| .glb (viewer) | 0.95 MB | 0.78 MB | — | 3k tris native, 60 fps |

## Quality rubric (1–5, judged on stills f36/f108)

| Criterion | A procedural | B scratch | Note |
|---|---|---|---|
| Silhouette | 4 | 5 | A's meta-rig bones don't match capsule proportions → slight arm oddity at peaks |
| Talking readability | 4 | 5 | A flaps continuously; B pauses + varies per "word" |
| Gesture variety | 2 | 5 | A runs the same sine loop on both; B: raise / wave / chop per line |
| Deformation artifacts | 3 | 5 | fitted 5-bone rig is cleaner than auto-weights on a foreign skeleton |

**Verdict: procedural gives ~80% of the quality at ~50% of the authoring cost
for a medium shot. For close-ups or acting, manual wins.**

## Track C (MB-Lab parametric humans) — measured

- Gen: 13.7 s + 13.8 s (one Blender session per character — MB-Lab singleton).
- Build: rig 0.0 s (ships rigged), anim 28 s (shape-key keyframing is slow),
  **render 607 s** (17k polys + skin textures vs 8 s for capsules = ~75x).
- L1 reads WORSE at identical framing: small realistic mouths vs capsule jaws.
- Lesson: generator quality (humans!) can lose to capsules on readability +
  speed. Match the generator to the shot, not to ambition.

## Track F (no Blender — Three.js) — measured

- ~230 lines of JS rebuild the L1 shot natively: 3k tris, 60 fps on mobile
  viewport, zero install, URL-shareable.
- Blender A/B play inside it as baked GLBs (55 fps, scrub-able) — the viewer
  is the play + edit hub for every track.
- Lesson: for L1-grade motion, the web path is 10x cheaper to ship than any
  Blender render; Blender wins when you need real rigs, GI, or footage.

## Track D (Ready Player Me) — BLOCKED, honestly reported by fleet agent

- models.readyplayer.me returns NXDOMAIN on all subdomains (verified via
  8.8.8.8), no API key in env, Wayback holds no archived RPM .glb.
- Evidence: `output/trackD_metrics.json` (blocked:true). ~10 min / ~4 rounds.
- Lesson: a generator you can't fetch scores zero — availability is a metric.

## Track E (MPFB MakeHuman, fleet agent) — measured

- Machine: model 0.4 s / rig 0.4 s / anim 0.3 s / **render 11.5 s** / total 12.6 s.
  2 humans (19k verts, 2x163 bones, jaw-bone L1), .blend 10.2 MB, .mp4 75 KB.
- No 1 GB asset pack needed (basemesh+rig ship in the 73 MB repo; flat tints
  double as speaker coding). MPFB 2.0.17 runs on Blender 4.0.2 with 3 local
  compat shims (see metrics notes). Agent cost: ~35 min / ~12 rounds.
- Lesson: MPFB is the efficiency upset — realistic humans at capsule-like
  render cost (11.5 s vs MB-Lab's 607 s) because flat shading skips SSS skin.

## Round 3 (checkpoint builders, 4 fleet agents × 10 min) — scored

| Metric | R3 web-three | R3 blender-api | R3 blender-gen | R3 free→web |
|---|---|---|---|---|
| First FULL set | 63 s | 64 s | 301 s | 302 s |
| Machine work ~ | 30 s | 11.5 s | 155 s | 30 s |
| Agent rounds | 14 | 8 | **1** (copied proven scripts: reuse dividend) | 12 |
| Rubric /6 | 6 | 6 | 5 (jaw tiny at framing) | 6 |
| Footprint w/ checkpoints | 0.8 MB | 12 MB | 76 MB | 5.8 MB |

Meta-findings: script-driven profiles deliver a FULL set in ~1 min;
the generator needs 5 min (gen cost). Both web agents independently chose
three.js — free-choice explicitly reasoned that 600 s budgets punish Blender
failure modes. Agent comfort revealed: web-three. No profile scored below
threshold, so no elimination — but Round 4 (playable game) only fits
interactive stacks: web-three + free-choice advance, blender-api stays as
render-contestant reserve.

## Key insight for the comparison

Keyframe COUNT misleads: A has ~320 keys, B ~88. A's keys cost zero decisions
(a `for` loop + `sin`); every one of B's 88 keys is an acting choice. Measure
**decisions, not keys** (and not compute seconds).

## Beginner bugs hit (all three are classics — worth knowing)

1. **API drift**: `bpy.ops.armature.human_metarig_add` (pre-4.0) no longer
   exists. Blender 4.x Rigify registers `bpy.ops.object.armature_human_metarig_add`.
   Found by reading `/usr/share/blender/scripts/addons/rigify/metarig_menu.py`.
2. **Apply scale before auto-weights**: joining into the torso object inherits
   its scale; un-applied non-uniform scale corrupts heat weighting. Fixed in B
   by joining everything + `transform_apply(scale=True)`.
3. **Primitive defaults bite**: `primitive_uv_sphere_add()` with no args gives
   radius 1.0, not 0.35 (giant-head render). Explicit > implicit.
4. **Bone-parenting via Python skips the inverse matrix** (children teleport).
   Avoided entirely: one joined skinned mesh, jaw/eyes ride on bone weights.

## Files

- `trackA_procedural/build_A.py`, `trackB_scratch/build_B.py` (re-runnable)
- `output/trackA.mp4`, `output/trackB.mp4`, `output/duet_sidebyside.mp4`
- `output/track{A,B}_{f01,f36,f108}.png`, `output/track{A,B}.blend`

## Suggested next rounds (each isolates one new layer)

1. Visemes: replace jaw-flap with 5 mouth shapes driven by a transcript.
2. Sound: add TTS dialogue (KIE Gemini TTS) + Rhubarb lip-sync.
3. Mixamo round: same shot with a Mixamo auto-rig + mocap clip (tests the
   "widely known generator" users actually mean for characters).
4. Face: shape-key blink/smile on top of the B rig.
