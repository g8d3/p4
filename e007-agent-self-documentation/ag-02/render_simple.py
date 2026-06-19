#!/usr/bin/env python3
"""Step 3C: Render simple text frames."""

import os
import subprocess
from PIL import Image, ImageDraw, ImageFont
from score import Segment

WIDTH = 608
HEIGHT = 1080
FPS = 30
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def render_segment_frame(segment: Segment, output_path: str, duration: float):
    """Render a segment as simple text on dark background."""
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(26, 26, 46))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype(FONT_BOLD, 36)
        font_body = ImageFont.truetype(FONT_MONO, 22)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # Label
    label_colors = {
        "hook": (91, 155, 213),
        "exploration": (112, 173, 71),
        "analysis": (255, 192, 0),
        "conclusion": (255, 100, 100),
    }
    label = segment.label.upper()
    color = label_colors.get(segment.label, (200, 200, 200))

    # Title
    draw.text((40, 80), label, fill=color, font=font_title)

    # Display text
    text = segment.display_text
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        bbox = draw.textbbox((0, 0), " ".join(current_line), font=font_body)
        if bbox[2] - bbox[0] > WIDTH - 80:
            lines.append(" ".join(current_line))
            current_line = []
    if current_line:
        lines.append(" ".join(current_line))

    y = HEIGHT // 2 - 100
    for line in lines[:10]:
        draw.text((40, y), line, fill=(224, 224, 224), font=font_body)
        y += 32

    # Stats
    stats = f"{len(segment.parts)} parts | score: {segment.score:.1f}"
    draw.text((40, HEIGHT - 100), stats, fill=(100, 100, 100), font=font_body)

    # Save PNG
    png_path = output_path.replace(".mp4", ".png")
    img.save(png_path)

    # Convert to video
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", png_path,
        "-t", str(duration),
        "-c:v", "h264_vaapi",
        "-vaapi_device", "/dev/dri/renderD128",
        "-vf", "format=nv12,hwupload",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return result.returncode == 0 and os.path.exists(output_path)
