# ag-04 — Video composer

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-07/pipeline-v2.md](../ag-07/pipeline-v2.md) — Weston GPU pipeline

## Command execution
All commands need `timeout <seconds>`. Examples:
- `timeout 10 ls, cat, grep` — quick checks
- `timeout 30 sudo apt install -y weston` — install
- `timeout 600 weston ...` — Weston server
- `timeout 600 godot4 ...` — Godot rendering
- `timeout 600 ffmpeg ...` — capture + encode

## Goal

Compose the final avatar podcast video with a pure GPU pipeline: Godot renders to a Weston display, ffmpeg captures it live with VAAPI. No intermediate PNG files.

## Wait

Do NOT start until `../ag-03/done.txt` exists.

## Cleanup

Before starting, remove artifacts from previous runs in this directory:
```
rm -f video_raw.avi video_nosound.mp4 video.mp4 done.txt
rm -f /tmp/render_pipe
```

## Inputs

- `../ag-03/seg_*.mp3` — one audio file per dialogue line, in order
- `../ag-03/timing.json` — metadata for each segment
- `../ag-06/avatar_a.png` — persona A avatar
- `../ag-06/avatar_b.png` — persona B avatar
- `../ag-06/podcast_bg.png` — background
- `../ag-02/script.md` — script for subtitle text
- `godot_project/render_podcast.gd` — needs modification

## Pipeline (GPU only, no PNGs)

**Key finding from ag-08**: Godot's FileAccess does NOT support FIFOs/named pipes. The pipe approach is impossible. Working approach: Godot renders to `frames.raw` (file), then ffmpeg VAAPI encodes it.

### Self-wake pattern

After launching ANY command in background, schedule a self-check with context. ALL commands go to background, even quick ones.

```bash
# Every command: background & + self-wake + continue working
(godot4 ...) &
PID=$!
(sleep 30; tmux send-keys -t a4 "Self-wake: PID=$PID, step=1/3 Godot render. Check if running, check frames.raw size." Enter) &

# Continue working on other things immediately
```

### Write render.sh

```bash
cat > render.sh << 'SCRIPT'
#!/bin/bash
set -e
export LIBVA_DRIVER_NAME=radeonsi
START_TS=$(date +%s)

echo "=== STEP 1/3: Godot render to frames.raw ==="
timeout 600 ~/.local/bin/godot4 --rendering-driver vulkan --display-driver headless \
  --path godot_project -- config.json &
GODOT_PID=$!

(while kill -0 $GODOT_PID 2>/dev/null; do
  echo "=== Godot PID $GODOT_PID running... ==="
  ps -p $GODOT_PID -o %cpu= --no-headers >> /tmp/cpu_samples.txt 2>/dev/null
  cat /sys/class/drm/card*/device/gpu_busy_percent >> /tmp/gpu_samples.txt 2>/dev/null
  sleep 5
done) &

wait $GODOT_PID 2>/dev/null

echo "=== STEP 2/3: VAAPI encode frames.raw ==="
timeout 120 ffmpeg -f rawvideo -pix_fmt rgba -s 608x1080 -framerate 25 \
  -i frames.raw \
  -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y video_nosound.mp4
rm -f frames.raw
END_TS=$(date +%s)

echo "=== STEP 3/3: Adding audio ==="
timeout 30 ffmpeg -i video_nosound.mp4 -i podcast_audio.mp3 \
  -c:v copy -c:a aac -shortest -y video.mp4

echo "=== Logging ==="
WALL_TIME=$((END_TS - START_TS))
VIDEO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4)
FILE_MB=$(stat --format=%s video.mp4 | awk '{printf "%.1f", $1/1024/1024}')
TOTAL_FRAMES=$(echo "$VIDEO_DUR * 25" | bc | cut -d. -f1)
RT_FACTOR=$(echo "scale=2; $VIDEO_DUR / $WALL_TIME" | bc)
CPU_AVG=$(awk '{sum+=$1; n++} END{printf "%.1f", sum/n}' /tmp/cpu_samples.txt 2>/dev/null || echo "0")
GPU_AVG=$(awk '{sum+=$1; n++} END{printf "%.1f", sum/n}' /tmp/gpu_samples.txt 2>/dev/null || echo "0")
CPU_PEAK=$(awk 'BEGIN{m=0}{if($1>m)m=$1}END{print m}' /tmp/cpu_samples.txt 2>/dev/null || echo "0")
GPU_PEAK=$(awk 'BEGIN{m=0}{if($1>m)m=$1}END{print m}' /tmp/gpu_samples.txt 2>/dev/null || echo "0")

echo "pipeline,wall_s,dur_s,fps,rt_factor,mb,frames,cpu_avg,gpu_avg,cpu_peak,gpu_peak,success" > render-log.csv
echo "pipe,$WALL_TIME,$VIDEO_DUR,25,$RT_FACTOR,$FILE_MB,$TOTAL_FRAMES,$CPU_AVG,$GPU_AVG,$CPU_PEAK,$GPU_PEAK,1" >> render-log.csv
rm -f /tmp/cpu_samples.txt /tmp/gpu_samples.txt /tmp/render_pipe
touch done.txt
echo "=== RENDER COMPLETE ==="

# Wake the agent one last time
tmux send-keys -t a4 "Pipeline complete. done.txt created." Enter
SCRIPT

chmod +x render.sh
bash render.sh &
echo "Render PID: $!"

# Schedule first wake in 10s
(sleep 10; tmux send-keys -t a4 "Check progress. Render PID: $(echo $!). Is Godot running? Any pipe errors?" Enter) &
```

The `render_podcast.gd` script already writes raw RGBA frame data to the pipe at `/tmp/render_pipe` (configured in config.json or hardcoded). If the pipe path differs, update the config or the ffmpeg command accordingly.

### 5. Add subtitles (if not rendered in Godot)
Use SRT with strict formatting rules (see Subtitles section).

## Format
**9:16 vertical** (608x1080).

## Subtitles

### Splitting rules (by word count + timing)

| Words in sentence | Max chunks | Max words per chunk |
|---|---|---|
| 1-4 | 1 | 4 |
| 5-10 | 2 | 5 |
| 11-15 | 3 | 5 |
| 16-20 | 4 | 5 |
| 21+ | 5 | 5 |

Split at natural boundaries (commas, periods, conjunctions). Never break a phrase across chunks.

### Minimum display time
Each subtitle must stay on screen for at least 1.2 seconds. If a chunk's audio is shorter, extend its display to 1.2s.

### Maximum display time
If a chunk would stay on screen longer than 3 seconds, split it further.

### Style
- Alternating colors: #FFFFFF, #FFD700, #00FF88, #FF6B6B, #6BCBFF
- Font size: at least 18px (readable on mobile)
- Bottom position (Alignment=2, MarginV=60)
- Font: Monospace

## Output
- `video.mp4` — final podcast, GPU-rendered, no PNGs

## Completion
When finished, create `done.txt` to trigger ag-05 review.
