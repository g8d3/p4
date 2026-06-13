from PIL import Image, ImageDraw, ImageFont
import json
import os
import subprocess

BG = "../ag-06/podcast_bg.png"
AV_A = "../ag-06/avatar_a.png"
AV_B = "../ag-06/avatar_b.png"
TIMING = "../ag-03/timing.json"
AUDIO = "podcast_audio.mp3"
OUTPUT = "video.mp4"

os.makedirs("seg_imgs", exist_ok=True)

bg = Image.open(BG).convert("RGBA")
av_a = Image.open(AV_A).convert("RGBA")
av_b = Image.open(AV_B).convert("RGBA")

with open(TIMING) as f:
    timing = json.load(f)

SEG_DIR = "../ag-03"

cx_a, cx_b = int(1920 * 0.3), int(1920 * 0.7)
cy = 540
av_size = 600

# Create per-segment images
segments = []

for i, seg in enumerate(timing):
    frame = bg.copy()
    speaker = seg["speaker"]

    s_a = 1.08 if speaker == "A" else 1.0
    s_b = 1.08 if speaker == "B" else 1.0

    r_a = av_a.resize((int(av_size * s_a), int(av_size * s_a)), Image.LANCZOS)
    x_a = int(cx_a - r_a.width / 2)
    y_a = int(cy - r_a.height / 2)
    frame.paste(r_a, (x_a, y_a), r_a)

    r_b = av_b.resize((int(av_size * s_b), int(av_size * s_b)), Image.LANCZOS)
    x_b = int(cx_b - r_b.width / 2)
    y_b = int(cy - r_b.height / 2)
    frame.paste(r_b, (x_b, y_b), r_b)

    out_path = f"seg_imgs/seg_{seg['segment']:03d}.png"
    frame.save(out_path)

    seg_file = f"{SEG_DIR}/{seg['file']}"
    dur = seg["duration"]
    segments.append((out_path, dur))
    print(f"  Segment {seg['segment']:3d}: {speaker} {dur:6.3f}s")

# Create concat file for ffmpeg
with open("concat.txt", "w") as f:
    for img_path, dur in segments:
        f.write(f"file '{os.path.abspath(img_path)}'\n")
        f.write(f"duration {dur:.6f}\n")
    # Last frame needs an extra entry without duration
    f.write(f"file '{os.path.abspath(segments[-1][0])}'\n")

print(f"\nComposing video with {len(segments)} segments...")
