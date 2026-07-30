#!/usr/bin/env bash
set -euo pipefail

# Assemble a storyboard video from images + audio files
# No API calls — just ffmpeg composition
#
# Usage:
#   ./kie-video.sh <config.json>
#
# Config format (JSON):
#   {
#     "intro": {"image": "title.jpg", "duration": 2},
#     "scenes": [
#       {"image": "scene1.jpg", "audio": "narration1.mp3", "label": "CDMX — Mexico"},
#       ...
#     ],
#     "output": "storyboard.mp4",
#     "resolution": "608x1080"
#   }

CONFIG="${1:?Usage: kie-video.sh <config.json>}"

if [ ! -f "$CONFIG" ]; then
    echo "Config not found: $CONFIG" >&2; exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Write the Python builder to a temp file
cat > /tmp/kie_video_builder.py << 'PYEOF'
import json, sys, subprocess

with open(sys.argv[1]) as f:
    cfg = json.load(f)

intro = cfg.get("intro", {})
scenes = cfg["scenes"]
output = cfg.get("output", "storyboard.mp4")
res = cfg.get("resolution", "608x1080")
w, h = res.split("x")

cmd = ["ffmpeg", "-y"]

intro_img = intro.get("image", "")
intro_dur = intro.get("duration", 2)
if intro_img:
    cmd += ["-loop", "1", "-t", str(intro_dur), "-i", intro_img]

for s in scenes:
    dur = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", s["audio"]],
        capture_output=True, text=True
    ).stdout.strip()
    s["_duration"] = dur or "5"
    cmd += ["-loop", "1", "-t", dur, "-i", s["image"]]

if intro_img:
    cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=" + str(intro_dur)]
for s in scenes:
    cmd += ["-i", s["audio"]]

filters = []

if intro_img:
    parts = []
    parts.append("[0:v]scale=" + w + ":" + h + ":force_original_aspect_ratio=increase,crop=" + w + ":" + h)
    it1 = cfg.get("intro_text", {}).get("line1", "")
    it2 = cfg.get("intro_text", {}).get("line2", "")
    if it1:
        parts.append("drawtext=text='" + it1 + "':fontsize=36:fontcolor=white:x=(w-text_w)/2:y=h/2-40:shadowcolor=black:shadowx=2:shadowy=2")
    if it2:
        parts.append("drawtext=text='" + it2 + "':fontsize=24:fontcolor=gray:x=(w-text_w)/2:y=h/2+10:shadowcolor=black:shadowx=2:shadowy=2")
    fc_body = ",".join(parts)
    filters.append(fc_body + "[v0]")

for i, s in enumerate(scenes):
    vi = i + 1 if intro_img else i
    label = s.get("label", "")
    txt = ""
    if label:
        txt = ",drawtext=text='" + label + "':fontsize=28:fontcolor=white:x=(w-text_w)/2:y=h-60:shadowcolor=black:shadowx=2:shadowy=2"
    filters.append("[" + str(vi) + ":v]scale=" + w + ":" + h + ":force_original_aspect_ratio=increase,crop=" + w + ":" + h + txt + "[v" + str(i+1) + "]")

concat_inputs = []
ai = len(scenes) + 1  # index of first audio input (0-based)
if intro_img:
    concat_inputs.append("[v0]")
    concat_inputs.append("[" + str(ai) + ":a]")
    ai += 1
else:
    ai = 0
for i in range(len(scenes)):
    concat_inputs.append("[v" + str(i+1) + "]")
    concat_inputs.append("[" + str(ai + i) + ":a]")

n_seg = len(scenes) + (1 if intro_img else 0)
filters.append("".join(concat_inputs) + "concat=n=" + str(n_seg) + ":v=1:a=1[v][a]")

fc = ";".join(filters)
# Write filter graph to a temp file to avoid shell quoting issues
with open('/tmp/kie_video_filter.txt', 'w') as f:
    f.write(fc)
cmd += ["-filter_complex_script", "/tmp/kie_video_filter.txt"]
cmd += ["-map", "[v]", "-map", "[a]"]
cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "23"]
cmd += ["-c:a", "aac", "-b:a", "128k", output]

# Simple quoting for the rest (no special chars expected)
print(" ".join("'" + p + "'" if " " in p else p for p in cmd))
PYEOF
python3 /tmp/kie_video_builder.py "$CONFIG" > /tmp/kie_video_cmd.sh
echo "Running ffmpeg..."
bash /tmp/kie_video_cmd.sh 2>&1 | tail -3
echo ""
ls -lh "$(python3 -c "import json; print(json.load(open('$CONFIG')).get('output','storyboard.mp4'))")"
