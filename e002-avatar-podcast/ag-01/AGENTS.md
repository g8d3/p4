# ag-01 — Avatar tool research

## Goal

Find the most economical way to create a video with talking avatars on this system.

## Task

Research and test available options. Write findings to `findings.md`.

### Research questions

1. Is Godot 4 installed? Can it render scenes to video via `--headless`?
   ```
   godot --version 2>/dev/null
   godot4 --version 2>/dev/null
   ```
2. What web-based approaches work? Can a headless browser render HTML+JS to video?
   ```
   chromium --headless --screenshot ...
   ```
3. Can ffmpeg composite talking-head style videos with just images + audio?
   (e.g., static PNG with subtle animation via ffmpeg filters)
4. Is there any other tool on this system usable for avatar video (OBS, Kdenlive, etc.)?

### Output

Write `findings.md` with:
- What is available and what is not
- For each working option: commands needed, quality, performance
- Recommended approach for ag-04 (the video composer)

### Dependencies

ag-04 needs your recommendation to choose the rendering tool.
