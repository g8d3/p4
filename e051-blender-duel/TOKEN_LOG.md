# TOKEN_LOG — AI cost metering for e051 (starts 2026-09-05)

Session model: `muse-spark-1.3-contributor` via provider `opencode-go`.
Per-track token counters are NOT exposed by this harness, so exact token
counts per track are unavailable. What IS recorded:

- Model id per session (see viewer footer).
- Agent working time (~min) and agent rounds (~loops) per track — counted
  from session history, shown in the viewer cost matrix. Rounds correlate
  with tokens: every debug loop is model I/O.

Approximate session history (this turn shapes the numbers):

| Track | Agent time ~ | Rounds ~ | Notes |
|---|---|---|---|
| A Rigify capsules | 15 min | 10 | 4.0 operator rename was the one surprise |
| B scratch capsules | 25 min | 8 | 3 classic bugs, all fixed same-session |
| C MB-Lab humans | 70 min | 20 | facing, skin, phenotype probes + 2 long renders |
| E MPFB humans | 35 min | 12 | muse-spark-1.3-contributor; machine model 0.4s / rig 0.4s / anim 0.3s / render 11.5s; 3 local 4.0-compat patches, no asset-pack needed; jaw-bone L1 verified |
| D RPM avatars | 10 min | 4 | BLOCKED: models.readyplayer.me NXDOMAIN on all subdomains, no API key, Wayback has no .glb — metrics carry blocked:true + evidence |

Rule going forward: any new track (RPM, MPFB, visemes, TTS) appends one row
here with model id + measured machine times + ~agent time/rounds, and the
viewer TRACKS object gets the same row. When the harness exposes token
counters, replace `rounds ~` with real counts.
| R3 web-three checkpoint | ~10 min | ~14 | muse-spark-1.3-contributor; single index.html (vendored three.js, no Blender); 9032 tris; jaw-diff 14.3; headless-sw ~16fps; 4 checkpoints with Playwright proofs, zero JS errors |
| R3 blender-gen (MPFB) | gen GEN DONE model=0.2s rig=0.2s total=0.7s -> charA.blend / GEN DONE model=0.2s rig=0.2s total=0.7s -> charB.blend; full TRACK-R3 TIMINGS  model=0.0s rig=0.0s anim=0.6s render=26.4s total=27.0s; wall 581s of 600s budget |
| R3 free-choice (web-three) | 10 min | 12 | muse-spark-1.3-contributor; machine stills ~5s / capture 6.3s x2 / ffmpeg ~3s; playable HTML + 6.3s x264 mp4, 144 logical frames @24fps, red-left/blue-right turn-taking verified on stills+mp4 frames |
| R3 blender-api (talking duo) | ~10 min | ~8 | muse-spark-1.3-contributor; machine model 0.1s / rig 0.1s / anim 0.0s / render 11.4s; blend 1.5MB mp4 0.11MB tris 3368 bones 10; min-viable at 43s wall, mp4 at 57s wall; 4/4 checkpoints final |
