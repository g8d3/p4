# ag-05 — Terminal demo: interactive pdw walkthrough

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`opencode-go/mimo-v2.5` (has vision for self-review)

## Goal

Record a live interactive demo of `pdw` (Puppet Display Wizard) from the terminal. While you use pdw, record BOTH:
1. A video of the virtual display (showing what you type)
2. An interaction log (everything you do, with timestamps)

After recording, produce TWO narration versions from the interaction log:
- **Version A (self)**: First-person narration. You describe what you did and why.
- **Version B (commentators)**: Two "video game commentators" react to what you did. Two different TTS voices alternating.

## Critical: You are NOT recording yourself

You are recording a **virtual display** (HEADLESS-N). Your terminal is not visible. All the viewer sees is the virtual display. You must:
1. Open a foot terminal in the virtual display
2. Type commands INSIDE that terminal (the viewer sees this)
3. Explain as you go — but your narration will be added AFTER (TTS), not live

So the workflow is:
1. Record the video + interaction log (video is silent, log captures everything)
2. Post-process: generate narration from the log, mix with video

## What to demonstrate

Use pdw interactively. Show at least these commands:

1. `pdw --help` — show the menu
2. `pdw ls` — show current state (displays, windows, VNC)
3. `pdw ds new` — create a new virtual display
4. `pdw w new HEADLESS-<N> foot --maximized` — open a terminal on it
5. `pdw w ls` — list windows
6. `pdw rec HEADLESS-<N> 10` — record for 10 seconds (or just show the command)
7. `pdw vnc new HEADLESS-<N>` — expose via VNC
8. `pdw clean` — cleanup

## Interaction log format

Record ALL commands and their output in `interaction-log.json`:

```json
[
  {"t": 0.0, "cmd": "pdw --help", "out": "pdw — Puppet Display Wizard\\nUsage: ...", "note": "showed the help menu"},
  {"t": 5.2, "cmd": "pdw ls", "out": "=== displays ===\\nHEADLESS-1 ...", "note": "current state has 1 display"},
  ...
]
```

Record timestamps relative to video start (0.0 = first frame). A simple way: prefix each command with `echo "=== $(date +%s%N) ==="` and parse later.

Or simpler: prefix with `echo ">>> $(printf %.1f $(echo $(date +%s.%N) - $START | bc))"` to get relative seconds.

## Recording the video

Use `../ag-00/bin/pdw` (not record.sh — pdw has more features):

```bash
# Ensure sway is running
../ag-00/bin/pdw init

# Create a fresh display for your demo
DISPLAY=$(../ag-00/bin/pdw ds new)   # returns HEADLESS-N

# Open foot terminal on it
../ag-00/bin/pdw w new "$DISPLAY" foot --maximized

# Record with unique name
../ag-00/bin/pdw rec "$DISPLAY" 45 ag05-terminal-demo
```

## Chroma sub-sampling fix

wf-recorder with libx264 produces yuv444p which VAAPI can't read. The pdw script handles this, but if you do manual encoding:

```bash
# If you get "no VAAPI support for yuv444p", convert first:
ffmpeg -y -i raw.mp4 -vf "format=nv12,hwupload" -c:v h264_vaapi final.mp4
```

## Two narration versions

### Version A — Self narration (file: `version-a-self.mp4`)

Generate a natural first-person script from the interaction log. Example:

> "So I started by checking what pdw can do — I ran pdw --help and it showed me all the commands. Then I created a new display, opened a terminal on it..."

Use `edge-tts` with voice `es-CO-SalomeNeural` (Colombian Spanish, female).

### Version B — Commentators (file: `version-b-commentators.mp4`)

Generate a script as if two game commentators are watching a live stream of you working. Example:

> **Commentator 1** (Salome, female): "Oh nice, he's checking the pdw help menu. Look at all those commands!"
> **Commentator 2** (Gonzalo, male): "Yeah man, I like the 'vnc' option — that's going to be useful for remote access."

Alternate between two voices:
- `es-CO-SalomeNeural` (female) — commentator 1
- `es-CO-GonzaloNeural` (male) — commentator 2

Mix both voices into a single audio track where they alternate every 1-3 sentences.

### edge-tts usage

```bash
# Single voice
edge-tts --voice es-CO-SalomeNeural --text "Hello world" --write-media hello.mp3

# For multi-voice, generate separate files and concatenate with ffmpeg
```

## Audio mixing

```bash
# Concatenate multiple TTS segments
ffmpeg -y -i "concat:seg1.mp3|seg2.mp3|seg3.mp3" -acodec copy full_narration.mp3

# Mix narration with original video
ffmpeg -y -i video.mp4 -i full_narration.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 output.mp4
```

## Output structure

```
output/terminal-pdw/
├── interaction-log.json          # raw interaction log
├── version-a-self.mp4            # video with self-narration
├── version-a-self.metadata.json
├── version-b-commentators.mp4    # video with commentator narration
└── version-b-commentators.metadata.json
```

## Self-review checklist

After producing EACH version:

- [ ] Video has visible content (not black/blank) — check with ffprobe
- [ ] Resolution 608x1080
- [ ] Interaction log has entries for every command
- [ ] Narration matches what's on screen (timestamps align)
- [ ] Audio is clear (edge-tts, not distorted)
- [ ] Version B has TWO distinct voices alternating
- [ ] File size > 500 KB (meaningful content)
- [ ] metadata.json present

## Pitfalls

- `pdw rec` defaults to name "recording" — ALWAYS pass a unique name or files collide
- The foot terminal starts maximized — type `clear` first if needed
- wf-recorder captures what's ON the virtual display — if nothing is open, video is blank
- Sway headless persists across calls — don't restart it between recordings
- chrome needs `--ozone-platform=wayland` and `WAYLAND_DISPLAY=wayland-1` for Wayland
