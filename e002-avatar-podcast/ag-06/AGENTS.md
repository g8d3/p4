# ag-06 — Avatar designer

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Command execution
All commands need `timeout <seconds>`.

## Goal

Design visually appealing avatar characters for the podcast video (persona A and B).

## Task

Create avatar images that look like podcast hosts. Iterate until the user approves.

### Approach

Use whatever tool produces the best result:
- **Godot 4**: create a simple 3D scene with two character models, render to PNG
- **ImageMagick**: draw cartoon-style avatars with `convert`
- **Chrome headless**: HTML+CSS+JS animated avatars, capture frame

Godot 4 is installed at `~/.local/bin/godot4`. Run headless:
```
godot4 --display-driver headless
```

### Output

Save avatar assets in this directory:

- `avatar_a.png`
- `avatar_b.png`
- `podcast_bg.png`

### Iteration

The user will review your designs. Keep iterating until they say "approve". Each iteration should build on the previous feedback.
