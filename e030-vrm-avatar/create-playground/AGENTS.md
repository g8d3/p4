# create-playground — creating avatars

Where avatars are **made and shown**: the three.js/three-vrm renderer clients,
the VRM character models, and the pose galleries that verify how a character
looks.

## Layout

```
create-playground/
├── clients/            # renderer clients (browser pages)
│   ├── viewer.html     # client-A (ag-01) + node_modules (three/three-vrm)
│   └── viewer-b.html   # client-B (ag-02) + client-b assets
├── models/
│   ├── model-a.vrm     # sample model (11 MB, glTF2)
│   └── model-b.vrm     # Seed-san (10.9 MB, glTF2)
└── poses/              # pose/expression verification screenshots
```

## What it is for

- Choosing/loading a character (`/models/*.vrm`)
- Viewing the avatar in a browser: `http://<host>:8787/viewer.html` (client-A)
  or `http://<host>:8787/viewer-b.html` (client-B)
- Creating a look: poses, expressions, camera, lighting
- Mobile: the pages run in any WebGL browser; WS url is derived from
  `location.host`, so they work over LAN.

## Rules

- This playground owns **characters and rendering only**. It has NO server,
  NO CLI, NO media. Everything that *drives* the avatar lives in
  [../control-playground](..) — the `/models/`, `/viewer*.html` routes are
  served by control-playground's server, which reads from here.
- Models are verified once (glTF magic + size), stored locally, never
  re-fetched in loops.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md)
- [../AGENTS.md](../AGENTS.md)