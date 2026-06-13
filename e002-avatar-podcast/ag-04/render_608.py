#!/usr/bin/env python3
"""Generate per-segment images at 608x1080 and concat file for ffmpeg."""
import json, os, math
from PIL import Image

W, H = 608, 1080
FPS = 25
OUTPUT = "seg_608"
BG = "../ag-06/podcast_bg.png"
AV_A = "../ag-06/avatar_a.png"
AV_B = "../ag-06/avatar_b.png"
TIMING = "../ag-03/timing.json"

os.makedirs(OUTPUT, exist_ok=True)

bg_full = Image.open(BG).convert("RGBA")
crop_x = (bg_full.width - W) // 2
bg = bg_full.crop((crop_x, 0, crop_x + W, H))

av_a = Image.open(AV_A).convert("RGBA")
av_b = Image.open(AV_B).convert("RGBA")

with open(TIMING) as f:
    timing = json.load(f)

# Layout: two avatars side by side in upper portion
AV_SIZE = 190  # scaled avatar size
GAP = 40
TOTAL_AV = 2 * AV_SIZE + GAP
av_x0 = (W - TOTAL_AV) // 2
av_y = 110

segments = []
for seg in timing:
    speaker = seg["speaker"]
    dur = seg["duration"]
    frame = bg.copy()

    s_a = 1.06 if speaker == "A" else 1.0
    s_b = 1.06 if speaker == "B" else 1.0

    r_a = av_a.resize((int(AV_SIZE * s_a), int(AV_SIZE * s_a)), Image.LANCZOS)
    x_a = av_x0 + (AV_SIZE - int(AV_SIZE * s_a)) // 2
    y_a = av_y + (AV_SIZE - int(AV_SIZE * s_a)) // 2
    frame.paste(r_a, (x_a, y_a), r_a)

    bx = av_x0 + AV_SIZE + GAP
    r_b = av_b.resize((int(AV_SIZE * s_b), int(AV_SIZE * s_b)), Image.LANCZOS)
    x_b = bx + (AV_SIZE - int(AV_SIZE * s_b)) // 2
    y_b = av_y + (AV_SIZE - int(AV_SIZE * s_b)) // 2
    frame.paste(r_b, (x_b, y_b), r_b)

    out_path = f"{OUTPUT}/seg_{seg['segment']:03d}.png"
    frame.save(out_path)
    segments.append((out_path, dur))
    print(f"  Seg {seg['segment']:3d}: {speaker} {dur:6.3f}s -> {out_path}")

# Create concat file
with open("concat_608.txt", "w") as f:
    for img_path, dur in segments:
        f.write(f"file '{os.path.abspath(img_path)}'\n")
        f.write(f"duration {dur:.6f}\n")
    # Last frame needs an extra entry without duration
    f.write(f"file '{os.path.abspath(segments[-1][0])}'\n")

print(f"\nDone. {len(segments)} segment images -> concat_608.txt")
