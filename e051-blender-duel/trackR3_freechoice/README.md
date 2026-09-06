# trackR3_freechoice — talking duo, web-three stack

Profile: `free-choice`. Tools chosen: **vanilla HTML + vendored three.js
(`viewer/vendor/three.module.js`, copied to `deliverables/vendor/`) +
Playwright (Chromium + SwiftShader) proof stills + MediaRecorder/ffmpeg mp4**.
No Blender in the loop.

## Why this choice

Under a 600 s budget the dominant risks are (a) Blender headless failure
modes (operator renames, weigh-paint surprises — see tracks A/B history) and
(b) EEVEE render-queue time. The web stack removes both: the scene is a
deterministic `pose(char, frame, talking)` function, so scrubbing,
still-capture, and 6 s video recording are all exact, and every checkpoint is
a working deliverable from minute 1. I am also simply fastest in HTML/JS,
and the task allows "playable OR rendered" — this delivers both.

## What was built

`deliverables/index.html` (self-contained + vendored three.js, works from any
static server or `file://`-adjacent http):

- Two capsule characters: red (screen-left, A) and blue (screen-right, B),
  angled toward each other + camera. Ground plane, hemisphere + sun + fill,
  fixed camera — same frozen-shot recipe as the Blender tracks.
- 6 s loop, 144 logical frames @24 fps. A talks f1–72, B talks f73–144.
- Talking layers L1+L2: jaw flap (gated sine envelope, shut when listening),
  head bob (speaker) / slow nod (listener), right-hand wave + left counter +
  lean-in (speaker), blink (both, offset phases).
- Transport: play/pause (button + space), frame scrub slider, frame/timecode
  readout, live speaker HUD + dialogue lines with active-speaker highlight,
  talk-speed and gesture-amount sliders, `?frame=N` deep link for proof stills.

## Proof

- `f01/f36/f108.png` — Playwright stills via `?frame=` (A-talking / B-talking).
- `duo.mp4` (+ `duo_capture.webm` source) — realtime 6.3 s canvas capture
  (`captureStream(24)` + MediaRecorder vp9 → libx264), `mp4_f36/mp4_f108.png`
  extracted to show turn-taking survived recording.

## Serve / verify

```bash
cd deliverables && python3 -m http.server 8741
# open http://localhost:8741/index.html (Playwright proof scripts in /tmp: r3proof.py, r3mp4.py)
```

## Checkpoints

`checkpoints/{01m,02m,05m,10m}/status.json` + file snapshots. `metrics.json`,
`done.txt`, TOKEN_LOG row at finish.
