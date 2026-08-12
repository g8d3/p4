# e024 ag-01 — composition sources

TSX compositions for the Diffusion Studio (dapi) experiment. All mount + render
locally, no generation credits.

| File | What it is | Narration |
|---|---|---|
| `dapi-titles.tsx` | Pure-composition title video (text cards + audio) | `../output/narration-dapi.mp3` (KIE Gemini TTS) |
| `p4-media.tsx` | Real p4 footage (e023 `episode.mp4`) in a PiP layout | `../output/narration-p4media.mp3` |
| `demo.tsx` | Final demo: "Diffusion Studio — the video editor your coding agents can drive" | `../output/demo-narration.mp3` |
| `demo-script.md` | Demo narration script (scene-by-scene) | — |
| `bench-ffmpeg.sh` | ffmpeg h264_vaapi baseline for the benchmark | — |

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
