# e030 — VRM Avatar Studio

A **single web page** where you both **create** and **control** a VRM avatar —
accessible from the phone over LAN. No CLI, no multi-client protocol, no video
pipeline: one small server + one page.

## Vision

Open `http://<host>:8787/` and get an **Avatar Studio**:

- **Create**: pick a character from a gallery (VRM models), replace the model
  on the canvas, save pose/expression snapshots.
- **Control**: on the same page — drag to rotate the camera, press expression
  buttons or sliders (happy, sad, surprised, blink…), set look-at targets,
  toggle idle behavior.
- Mobile-first: the page must be usable and readable on the phone's vertical
  browser (WebGL + touch).

Later phases (NOT now): agents using the studio to produce many avatars,
narration/lip-sync, talking-avatar videos.

## Scope rules

- One deliverable, one agent (ag-01): a tiny Node server (serves the page +
  the `.vrm` files) + one page that creates and controls.
- Skip: CLI, WebSocket protocol, second client, capture scripts, video
  encoding, performance scripts. If a feature isn't needed to "create and
  control on one page", it stays out of v1.
- The `.vrm` model(s) may be shared at `ag-01-avatar-studio/models/`
  (verified once: glTF magic + size; never re-fetch in loops).

## Structure

```
e030-vrm-avatar/
├── AGENTS.md
└── ag-01-avatar-studio/    the whole studio (server + page + models) → tmux 30-1
    ├── AGENTS.md
    └── output/             screenshots proving create+control work
```

Future agents (eg. ag-02 "many avatars", ag-03 "video") will be added later as
separate `ag-0N/` dirs, each reading the studio's files.

## Success criteria (ag-01)

- From a phone on the LAN, the page loads, a character appears (not black),
  you can pick another character, rotate it, trigger ≥3 expressions/look-at,
  and save a snapshot.
- The server keeps running headless; the page connects simply (no exotic
  browser flags for a REAL device — the flags matter only for headless Chrome
  verification).
- `output/` contains screenshots of at least two characters in different
  expressions, and the models are verified + documented.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command/timeout rules, browser/CDP, Wayland/sway, TTS, video
- [../AGENTS.md](../AGENTS.md) — p4 index