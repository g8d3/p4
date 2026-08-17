# control-playground — controlling avatars

Where avatars are **driven**: the control API server, the `avatar` CLI, speech
media, performance scripts, and the video pipeline that turns a performance
into a final output.

## Layout

```
control-playground/
├── server/            # avatar-server: HTTP+WS control API (port 8787)
│   ├── server.js      # serves /viewer.html, /viewer-b.html, /models/*, /media/*
│   ├── bin/           # avatar-server launcher, capture-frame helpers
│   └── node_modules/
├── cli/               # `avatar` CLI + cdp helpers + build-viewer
├── media/             # narration.mp3, mouth.json (lip-sync energy timeline)
├── scripts/           # demo-script.json, performance.json, transcript.*
└── output/            # capture.mp4, final.mp4, metadata.json, done.txt
```

## What it is for

- **API**: `POST /cmd` + WS on `127.0.0.1:8787` → `load`, `expression`,
  `lookAt`, `bone`, `animation`, `speak`, `setIdle`, `inspect` (protocol in
  `server/bin/server-contract.md`).
- **CLI**: `server/bin/avatar <cmd> …` drives either client (`--client B`).
- **Speaking**: `speak <audio> <mouth.json>` plays narration + lip sync.
- **Scripts**: `script <performance.json>` replays a timed performance.
- **Video**: sway headless 608x1080 + wf-recorder → `encode_vaapi.sh` (H264
  VAAPI) → `final.mp4` + `metadata.json`.

## Rules

- This playground owns **control and production only**. It reads characters from
  [../create-playground](..) (`/models/*` served from there) — it never edits
  them.
- Alone, no client is running: the server waits for browser pages to connect
  (WS). A client is optional — the API works with zero clients but commands
  return "no clients connected".
- Final videos are always `h264_vaapi` (verify `stream_tags=encoder`).
- On headless WebGL: Chrome ≥137 needs `--enable-unsafe-swiftshader`.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md)
- [../AGENTS.md](../AGENTS.md)