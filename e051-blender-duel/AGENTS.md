# e051 — 3D Game Build Showdown (meta-experiment)

ONE experiment of experiments, living entirely in this dir (deliberately NOT
one dir per e###): every round compares methods for the AGENT to build a 3D
game — same shot, same metrics, one URL (`viewer/index.html`).

## Rounds (not separate experiments)

- **Round 1 — talking duo**: Web native vs Track A (Rigify capsules) vs
  Track B (scratch capsules) vs Track C (MB-Lab humans). Question: procedural
  vs hand-built for a simple animated scene?
- **Round 2 — human generators**: Track E (MPFB, delivered) vs Track D (RPM,
  BLOCKED — endpoint retired). Question: which free human generator works
  headless, and at what render cost?
- **Round 3 (RUNNING) — checkpoint builders**: ONE 10-min run per tool profile with
  snapshots at 1/2/5/10 min (checkpoints beat separate time-boxed agents: same
  time-series data at 1/4 the agent cost). Profiles (widest useful range):
  `web-three` (my strongest: vendored three.js + Playwright proof),
  `blender-api` (proven bpy headless), `blender-gen` (MPFB headless),
  `free-choice` (agent picks — reveals tool comfort). Dirs `trackR3_<profile>/`
  with `checkpoints/{01m,02m,05m,10m}/` + `metrics.json` + rubric score.
  Elimination rule: after each round, drop profiles that win no matrix row AND
  score below threshold; winners advance to longer budgets. Top-2 + 1 newcomer.
- **Round 4 (next) — playable**: top-2 profiles from R3 build input + goal +
  game loop (first step to GAME), 30-min budget.

## Tracks

## The shot (frozen for both tracks)

- 2 capsule characters (Red left, Blue right), facing each other + camera.
- 6 sec, 24 fps, 144 frames, 1280x720 @50% preview (=640x360), EEVEE.
- Ground plane, 1 SUN + 1 AREA fill, 1 fixed camera.
- Dialogue (fake, no audio): A talks frames 1-72, B talks 73-144.
- "Talking" = jaw open/close + head bob + hand gestures (+ blink if time).

## Tracks

| | Track A: procedural | Track B: from scratch |
|---|---|---|
| Mesh | Python loop places primitives (parameterized) | Same primitives, explicit step-by-step placement |
| Rig | Rigify Human Meta-Rig (ships with Blender, widely known generator) + automatic weights | Custom 5-bone armature built bone-by-bone + automatic weights |
| Animation | Computed sine-loop keyframes (math, no acting choices) | Hand-authored keyframes matched to fake dialogue (acting choices) |
| Scene/light/camera/render | SHARED (identical settings) | SHARED |

Only rig+animation differ. Modeling is capsules in both (deliberate: keeps the
test to minutes; a sculpt-vs-parametric-human test would take hours).

## More tracks (added after the first duel)

- `trackC_mblab/` — MB-Lab 1.8.1 parametric HUMANS (female+male, 17k polys,
  71-bone rigs, `Expressions_mouthOpen_max` shape key for the jaw). Needs
  `gen_char.py` runs first (one Blender session per character: MB-Lab is a
  singleton), then `build_C.py` appends both into the shared scene.
- `trackF_web/` — NO BLENDER at all: `viewer/index.html` (Three.js, vendored
  in `viewer/vendor/`) rebuilds the shot natively + plays the Blender tracks
  as baked `.glb` (see `export_glb.py`). The viewer is also the playable +
  editable front-end: orbit/zoom, play/pause/scrub, talk-speed / gesture /
  jaw sliders, speaker select, colors, camera presets, live fps+tris readout.
  Serve: `cd viewer && python3 -m http.server` (modules need http).

## Files

- `BRIEF.md` — the improved instruction (what "talking" means + full pipeline).
- `trackA_procedural/build_A.py` — run: `blender -b -P trackA_procedural/build_A.py`
- `trackB_scratch/build_B.py` — run: `blender -b -P trackB_scratch/build_B.py`
- `output/` — blends, stills, videos, `TIMINGS.md`.

## Experiment registry + fleet rules (continuous experiments)

The viewer (`viewer/index.html`) holds an `EXPERIMENTS` registry: each
experiment contributes `{ tracks, matrix }` like e051, picked from the `#exp`
selector. New experiments append entries; the matrix highlights per-row winners.

Fleet agents (RPM, MPFB, and all future tracks) obey this contract:

1. Work ONLY inside your own `trackX_name/` dir. Never edit `viewer/index.html`.
2. Meter everything: `time` every Blender run; record model/rig/anim/render
   seconds from script output; count your own build/test rounds.
3. Deliver: `output/<track>_<f01,f36,f108>.png`, `output/<track>.mp4`,
   `output/<track>.blend`, and `output/<track>_metrics.json` with
   `{model_s, rig_s, anim_s, render_s, total_s, blend_bytes, mp4_bytes,
   tris, bones, agent_min_approx, agent_rounds, notes}`.
4. Append one row to `TOKEN_LOG.md` (model id + your numbers).
5. Write `done.txt` + notify when finished. The coordinator wires your metrics
   into the viewer registry; the page is the single URL for all results.

## Run

```bash
time blender -b -P trackA_procedural/build_A.py
time blender -b -P trackB_scratch/build_B.py
```

Each script writes its own .blend + 3 stills + 1 mp4 into `output/` and prints
its stage timings to stdout.
