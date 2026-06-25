# ag-06 — Browser demo: GitHub/Trendshift/HuggingFace trends

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`opencode-go/mimo-v2.5` (has vision for self-review)

## Goal

Record a live interactive demo browsing AI/tech trends in the browser using a virtual display. While you browse, record BOTH:
1. A video of the virtual display (showing browser navigation)
2. An interaction log (URLs visited, what you see, timestamps)

After recording, produce TWO narration versions from the interaction log:
- **Version A (self)**: First-person narration describing what you found.
- **Version B (commentators)**: Two "video game commentators" reacting to the trends.

## Sites to visit (spend ~10s each)

1. **GitHub Trending** — https://github.com/trending
2. **Trendshift** — https://trendshift.net (or similar trend aggregator)
3. **Hugging Face Papers** — https://huggingface.co/papers
4. **Artificial Analysis** — https://artificialanalysis.ai

Scroll a bit on each to show content. The video should be 45-60 seconds total.

## Critical: Chrome profile

Use the same profile as `nova-chrome` but adapted for Wayland:

```bash
WAYLAND_DISPLAY=wayland-1 google-chrome \
  --ozone-platform=wayland \
  --user-data-dir="$HOME/profiles/chrome-main" \
  --profile-directory="Profile 1" \
  --no-first-run \
  --no-default-browser-check \
  --new-window "https://github.com/trending" &
```

If chrome is already running with that profile (lock conflict), use a temp profile:
```bash
WAYLAND_DISPLAY=wayland-1 google-chrome \
  --ozone-platform=wayland \
  --user-data-dir="/tmp/chrome-trends-$$" \
  --no-first-run \
  --new-window "https://github.com/trending" &
```

## Interaction log format

Record ALL URLs visited and observations in `interaction-log.json`:

```json
[
  {"t": 0.0, "url": "https://github.com/trending", "action": "opened", "note": "GitHub trending shows AI repos dominating"},
  {"t": 12.5, "url": "https://github.com/trending", "action": "scrolled", "note": "saw langchain, ollama, stable-diffusion"},
  {"t": 18.0, "url": "https://trendshift.net", "action": "opened", "note": "loaded, showing dev tools rankings"},
  ...
]
```

Record timestamps relative to video start. Use `date +%s.%N` for precision.

## Recording the video

```bash
# Ensure sway is running with at least 2 displays
../ag-00/bin/pdw init
../ag-00/bin/pdw ds new   # ensure you have a display for chrome (reuses free displays)

# Remove lock files before launching Chrome
rm -f "$HOME/profiles/chrome-main/SingletonLock" "$HOME/profiles/chrome-main/Profile 1/SingletonLock"

# Open chrome on HEADLESS-<N> — arguments MUST be separate (not one quoted string)
../ag-00/bin/pdw w new HEADLESS-2 google-chrome --ozone-platform=wayland \
  --user-data-dir="$HOME/profiles/chrome-main" \
  --profile-directory="Profile 1" \
  --no-first-run --no-default-browser-check \
  --new-window "https://github.com/trending"

# Navigate between sites with wtype (Ctrl+L, type URL, Enter)
WAYLAND_DISPLAY=wayland-1 wtype -M ctrl l
sleep 0.5
WAYLAND_DISPLAY=wayland-1 wtype "https://next-site.com"
WAYLAND_DISPLAY=wayland-1 wtype -k return

# Record with wf-recorder directly (background, then kill)
nohup env WAYLAND_DISPLAY=wayland-1 wf-recorder -f raw.mp4 -o HEADLESS-2 --no-dmabuf --no-damage -c libx264 -r 25 &
RECPID=$!
disown
# ... do browsing ...
kill $RECPID

# Encode with VAAPI
ffmpeg -y -i raw.mp4 -vaapi_device /dev/dri/renderD128 -vf "format=nv12,hwupload" -c:v h264_vaapi -b:v 2M final.mp4
```

## Two narration versions

### Version A — Self narration (file: `version-a-self.mp4`)

Write a natural script based on the interaction log:

> "I started on GitHub Trending — wow, AI repositories are everywhere. LangChain is still going strong. Then I checked Trendshift to compare..."

Use `edge-tts` with voice `es-CO-SalomeNeural` (Colombian Spanish).

### Version B — Commentators (file: `version-b-commentators.mp4`)

Two commentators reacting like a sports broadcast:

> **Commentator 1** (Salome, female): "He's on GitHub Trending and — oh! LangChain at number 2 again!"
> **Commentator 2** (Gonzalo, male): "No surprise there, man. That framework has been killing it all year."
> **C1**: "Now he's switching to Trendshift... let's see what's different over there."
> **C2**: "Different platform, same story — AI tools are taking over."

Alternate between:
- `es-CO-SalomeNeural` (female) — commentator 1
- `es-CO-GonzaloNeural` (male) — commentator 2

### edge-tts

```bash
edge-tts --voice es-CO-SalomeNeural --text "..." --write-media seg1.mp3
edge-tts --voice es-CO-GonzaloNeural --text "..." --write-media seg2.mp3

# Concatenate in order
ffmpeg -y -i "concat:seg1.mp3|seg2.mp3|..." -acodec copy full_narration.mp3
```

## Output structure

```
output/browser-trends/
├── interaction-log.json              # raw interaction log
├── version-a-self.mp4                # video with self-narration
├── version-a-self.metadata.json
├── version-b-commentators.mp4        # video with commentator narration
└── version-b-commentators.metadata.json
```

## Self-review checklist

- [ ] Video shows real browser content (no black/blank)
- [ ] Resolution 608x1080
- [ ] At least 3 different sites visited
- [ ] Interaction log has entries for each navigation
- [ ] Narration matches what's shown (timestamps align)
- [ ] Version B has TWO distinct voices alternating
- [ ] File size > 1 MB (browser content should be larger)
- [ ] metadata.json present

## Pitfalls

- Chrome with Wayland may take 5-10s to start — wait after `pdw w new`
- The `--user-data-dir` must NOT be in use by another chrome instance
- If chrome is already running with that profile, use `/tmp/chrome-trends-$$`
- Sites may load slowly on first visit (cache miss) — wait for full load
- pdw rec defaults name to "recording" — ALWAYS pass a unique name
- If chrome doesn't appear, check `pdw w ls` to confirm it's on the right display
- **CRITICAL**: `pdw w new` arguments must be separate, NOT a single quoted string. Use `pdw w new HEADLESS-2 google-chrome --flag --flag2`, NOT `pdw w new HEADLESS-2 "google-chrome --flag --flag2"`. The latter breaks `"$@"` expansion inside pdw.
- **wtype key names**: Use `-M ctrl` (lowercase) for modifier. Do NOT use `-k ctrl` at end. Correct: `wtype -M ctrl l` for Ctrl+L.
- **Chrome on Wayland headless**: Works only with SINGLE sway instance. Multiple sway instances cause "Broken pipe" fatal error.
- **pdw idempotent init**: `pdw init` is now safe to call multiple times — won't restart already-running sway.
- **Display ownership**: Always `pdw claim HEADLESS-N` before using a display. Release with `pdw release HEADLESS-N`.
- **Remove Singleton locks**: Before launching Chrome, always remove lock files: `rm -f "$HOME/profiles/chrome-main/SingletonLock" "$HOME/profiles/chrome-main/Profile 1/SingletonLock"`

## Session learnings (2025-06-25)

### What worked
- `pdw w new` with separate args works reliably
- wtype `-M ctrl l` works for Ctrl+L shortcut in Chrome on Wayland
- VAAPI encoding at ~25x real time for 608x1080
- edge-tts with Colombian voices works well for both versions

### What was fixed
- `pdw init` is now idempotent — no longer kills existing sway
- `pdw clean` defaults to safe mode (only own claims), `--force` for everything
- `pdw w new` quoting bug fixed (was passing literal single quotes to Python)
- `pdw w new` timeout increased from 3s to 30s for slow apps like Chrome
- `pdw ds new` reuses free displays before creating new ones
- Display ownership added (`claim`/`release` commands + lock files)
- `pdw rec` now uses `timeout` for ffmpeg encode step

### Reactive approach (not deterministic scripts)
- Don't write long scripts that ignore mid-execution errors
- Verify each step: check Chrome alive, check wtype success, check file sizes
- Adapt course when something fails instead of blindly continuing
- Use grim for screenshots to verify content (though headless can't show visually)
