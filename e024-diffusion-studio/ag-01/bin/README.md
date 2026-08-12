# e024 ag-01 — composition sources

TSX compositions for the Diffusion Studio (dapi) experiment. All mount + render
locally, no generation credits.

| File | What it is | Narration |
|---|---|---|
| `dapi-titles.tsx` | Pure-composition title video (text cards + audio) | `../output/narration-dapi.mp3` (KIE Gemini TTS) |
| `p4-media.tsx` | Real p4 footage (e023 `episode.mp4`) in a PiP layout | `../output/narration-p4media.mp3` |
| `demo.tsx` | Final demo v2: "Diffusion Studio — the video editor your coding agents can drive" | `../output/demo-narration.mp3` |
| `demo-script.md` | Demo narration script (scene-by-scene) | — |
| `bench-ffmpeg.sh` | ffmpeg h264_vaapi baseline for the benchmark | — |

## Demo v2 improvements (applied 2026-08-12)

1. Gradient background + cyan badge visible from frame 0 (no black frame).
2. Bright PiP of our own render with cyan glow border.
3. Real assets: `asset-composition.png` (clean `dapi node capture`) and
   `asset-terminal-crop.png` (grim capture of dapi running in a foot terminal).
4. Captions timed from the local Parakeet SRT (dapi's `<captions>` needs the
   hosted backend: `Missing authorization token`).
5. Inter font everywhere, entrance fade on cards, ambient music bed
   (`ambient-bed.mp3`, synthesized offline with ffmpeg, -30 dB), end card with
   repo CTA, 8 Mbps video bitrate.

## Image sourcing priority (where do the images come from?)

Documented in fundamentals: `e000-fundamentals/sources.md` →
**Image sourcing priorities**. Summary: session captures → existing p4 media →
stock → KIE Seedream generation → editor-native `generate.*` → AI video frames.
Never generate what you can capture; never generate what p4 already has.

## Mount + render

```sh
# editor must be running (see ../output/exploration.md)
dapi mount bin/demo.tsx
SCENE=$(dapi node tree | python3 -c \
  "import sys,json; print([json.loads(l)['id'] for l in sys.stdin if json.loads(l).get('name')=='Demo'][0])")
dapi node render $SCENE -o output/demo.mp4 \
  --json '{"format":"mp4","video":{"codec":"avc","bitrate":8000000},"audio":{"codec":"opus"}}'
```

**Note:** the render's default AAC audio is unsupported in Chromium/WebCodecs on
this build — always pass `"audio":{"codec":"opus"}`.

## Verify

```sh
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height -of default=noprint_wrappers=1 output/demo.mp4
ffmpeg -y -v error -ss 5 -i output/demo.mp4 -frames:v 1 /tmp/f.png && python3 -c "from PIL import Image; im=Image.open('/tmp/f.png').convert('L'); print(sum(1 for p in im.getdata() if p>180))"
```
