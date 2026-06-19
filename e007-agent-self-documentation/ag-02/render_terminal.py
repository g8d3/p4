#!/usr/bin/env python3
"""Step 3A: Render styled terminal frames with Pillow."""

import os
from PIL import Image, ImageDraw, ImageFont
from parse import Part
from score import Segment

WIDTH = 608
HEIGHT = 1080
FPS = 30

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# Colors
BG_COLOR = (26, 26, 46)
HEADER_BG = (40, 40, 60)
USER_COLOR = (91, 155, 213)       # blue
AGENT_COLOR = (112, 173, 71)      # green
TOOL_COLOR = (255, 192, 0)        # yellow
REASONING_COLOR = (102, 102, 102) # gray
PATCH_COLOR = (255, 165, 0)       # orange
TEXT_COLOR = (224, 224, 224)      # light gray
PROMPT_COLOR = (128, 128, 128)    # dim gray


def render_segment_frame(segment: Segment, output_path: str, duration: float):
    """Render a segment as a styled terminal frame video."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font_header = ImageFont.truetype(FONT_BOLD, 28)
        font_body = ImageFont.truetype(FONT_MONO, 22)
        font_small = ImageFont.truetype(FONT_MONO, 16)
    except Exception:
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Header bar
    draw.rectangle([(0, 0), (WIDTH, 60)], fill=HEADER_BG)
    draw.text((20, 15), "OpenCode Session", fill=TEXT_COLOR, font=font_header)

    # Render each part
    y = 80
    line_height = 28
    max_lines = (HEIGHT - 120) // line_height

    for part in segment.parts[:max_lines]:
        if y > HEIGHT - 40:
            break

        if part.type == "text":
            # Check if it looks like a user message
            text = part.text
            if len(text) < 200:  # likely user message
                draw.text((20, y), f"$ {text[:70]}", fill=USER_COLOR, font=font_body)
                y += line_height
                if len(text) > 70:
                    draw.text((40, y), text[70:140], fill=USER_COLOR, font=font_body)
                    y += line_height
            else:
                # Agent response
                draw.text((20, y), f"Agent:", fill=AGENT_COLOR, font=font_body)
                y += line_height
                # Wrap text
                words = text.split()
                line = ""
                for word in words:
                    test = f"{line} {word}".strip()
                    if len(test) > 55:
                        draw.text((40, y), line, fill=TEXT_COLOR, font=font_body)
                        y += line_height
                        line = word
                        if y > HEIGHT - 40:
                            break
                    else:
                        line = test
                if line and y < HEIGHT - 40:
                    draw.text((40, y), line, fill=TEXT_COLOR, font=font_body)
                    y += line_height

        elif part.type == "tool":
            tool = part.tool_name
            if part.tool_input:
                inp = part.tool_input[:60]
                draw.text((20, y), f"$ {tool} {inp}", fill=TOOL_COLOR, font=font_body)
            else:
                draw.text((20, y), f"$ {tool}", fill=TOOL_COLOR, font=font_body)
            y += line_height
            if part.tool_output:
                out = part.tool_output[:80].replace("\n", " ")
                draw.text((40, y), out, fill=PROMPT_COLOR, font=font_small)
                y += 20

        elif part.type == "reasoning":
            chars = len(part.text)
            draw.text((20, y), f"  thinking... ({chars} chars)", fill=REASONING_COLOR, font=font_small)
            y += 22

        elif part.type == "patch":
            draw.text((20, y), f"  edit: {part.file_path[:60]}", fill=PATCH_COLOR, font=font_body)
            y += line_height

        elif part.type in ("step-start", "step-finish"):
            pass  # skip step markers

        y += 4  # spacing

    # Save PNG
    png_path = output_path.replace(".mp4", ".png")
    img.save(png_path)

    # Convert to video
    import subprocess
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
