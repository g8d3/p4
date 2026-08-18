# e031 — Wife's Dream (paper-cutout Three.js narrative player)

A single-page, single-file 3D web experience: a **multi-act dream narrative in a
retro paper-cutout (telenovela) aesthetic**, rendered with Three.js/WebGL,
narrated via TTS, with subtitles, camera animation, and full video-player
controls. Accessible from the phone over LAN, like e030.

## Scope

- One deliverable, one agent (ag-01): a tiny Node server + one self-contained
  `index.html` (Three.js scene, storyboard, TTS, subtitles, controls).
- The 9-act dream narrative and design system are fully specified in
  [plan.md](plan.md). Follow it exactly: paper-cutout layered planes,
  glassmorphism HUD, KIE Gemini TTS (primary) / Deepgram (alt) / Web Speech
  (fallback).
- Skip: video encoding, capture scripts, multi-agent coordination.

## Structure

```
e031-wife-dream/
├── AGENTS.md
├── plan.md              the spec (design system, TTS, storyboard, structure)
└── ag-01-dream-player/  the whole player (server + page) → tmux 31-1
    ├── AGENTS.md
    ├── index.html       self-contained page (CSS + JS inline, CDN libs)
    ├── server.js        tiny Node static server on 0.0.0.0:8788
    └── output/          screenshots + verification
```

## Success criteria (ag-01)

- From a phone on the LAN, the page loads and renders the 3D paper-cutout
  scene (not black), all 9 scenes are reachable via controls + auto-advance,
  narration plays via a TTS provider, subtitles track the audio, and the HUD
  (play/pause, scrubber, volume, provider select, fullscreen) works.
- Server reachable from LAN, stays up without a client.
- `output/` contains screenshots of the rendered scene (≥2 scenes) and the HUD.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command/timeout rules, browser/CDP, TTS, video
- [../AGENTS.md](../AGENTS.md) — p4 index
