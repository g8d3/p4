from PIL import Image
import json
import math
import os
import sys

FPS = 25
OUTPUT = "frames"
BG = "../ag-06/podcast_bg.png"
AV_A = "../ag-06/avatar_a.png"
AV_B = "../ag-06/avatar_b.png"
TIMING = "../ag-03/timing.json"

os.makedirs(OUTPUT, exist_ok=True)

bg = Image.open(BG).convert("RGBA")
av_a = Image.open(AV_A).convert("RGBA")
av_b = Image.open(AV_B).convert("RGBA")

with open(TIMING) as f:
    timing = json.load(f)

total_dur = sum(s["duration"] for s in timing)
total_frames = int(math.ceil(total_dur * FPS))
print(f"Rendering {total_frames} frames...")

pad = 600
cx_a, cx_b = int(1920 * 0.3), int(1920 * 0.7)
cy = 540

for f_idx in range(total_frames):
    t = f_idx / FPS
    cum = 0.0
    speaker = ""
    for s in timing:
        cum += s["duration"]
        if t < cum:
            speaker = s["speaker"]
            break

    frame = bg.copy()
    s = 1.0 + 0.03 * math.sin(t * 10.0) if speaker == "A" else 1.0
    resized = av_a.resize((int(pad * s), int(pad * s)), Image.LANCZOS)
    x = int(cx_a - resized.width / 2)
    y = int(cy - resized.height / 2)
    frame.paste(resized, (x, y), resized)

    s = 1.0 + 0.03 * math.sin(t * 10.0) if speaker == "B" else 1.0
    resized = av_b.resize((int(pad * s), int(pad * s)), Image.LANCZOS)
    x = int(cx_b - resized.width / 2)
    y = int(cy - resized.height / 2)
    frame.paste(resized, (x, y), resized)

    frame.save(f"{OUTPUT}/frame_{f_idx + 1:05d}.png")

    if (f_idx + 1) % 200 == 0:
        print(f"  Frame {f_idx + 1}/{total_frames}")

print(f"Done. {total_frames} frames in {OUTPUT}/")
