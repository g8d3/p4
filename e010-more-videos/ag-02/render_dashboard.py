#!/usr/bin/env python3
"""
render_dashboard.py - Render comparison dashboard for resource monitoring video.

Reads metrics JSON files and GPU CSV data, renders frames showing the comparison.
"""

import json
import csv
import sys
import os
import math
from PIL import Image, ImageDraw, ImageFont

WIDTH = 608
HEIGHT = 1080

# Colors
BG = (15, 15, 25)
CARD_BG = (25, 30, 45)
CARD_BORDER = (50, 60, 90)
TEXT_WHITE = (240, 240, 250)
TEXT_DIM = (140, 150, 170)
TEXT_ACCENT = (100, 180, 255)
GREEN = (80, 220, 120)
ORANGE = (255, 180, 60)
RED = (255, 80, 80)
BLUE = (80, 160, 255)
PURPLE = (180, 100, 255)
BAR_BG = (35, 40, 60)
TITLE_COLOR = (120, 200, 255)


def get_font(size):
    """Get a monospace font."""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_rounded_rect(draw, xy, radius, fill, outline=None):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_bar(draw, x, y, w, h, value, max_val, color, label="", font=None):
    """Draw a horizontal bar chart."""
    # Background
    draw_rounded_rect(draw, (x, y, x + w, y + h), radius=4, fill=BAR_BG)
    # Fill
    if max_val > 0:
        fill_w = max(4, int(w * min(value / max_val, 1.0)))
    else:
        fill_w = 4
    draw_rounded_rect(draw, (x, y, x + fill_w, y + h), radius=4, fill=color)
    # Label
    if font and label:
        draw.text((x + w + 8, y + h // 2 - 6), label, fill=TEXT_DIM, font=font)


def render_frame(frame_num, metrics_left, metrics_right, gpu_data, total_frames):
    """Render a single dashboard frame."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    font_title = get_font(28)
    font_label = get_font(18)
    font_value = get_font(36)
    font_small = get_font(14)
    font_tiny = get_font(12)

    y = 20

    # Title
    draw.text((WIDTH // 2 - 180, y), "Resource Usage Comparison", fill=TITLE_COLOR, font=font_title)
    y += 45

    # Subtitle with model names (abbreviated to fit)
    left_name = metrics_left.get("model", "Provider A") if metrics_left else "Waiting..."
    right_name = metrics_right.get("model", "Provider B") if metrics_right else "Waiting..."
    # Center the vs text
    vs_text = f"{left_name}  vs  {right_name}"
    bbox = draw.textbbox((0, 0), vs_text, font=font_label)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, y), vs_text, fill=TEXT_DIM, font=font_label)
    y += 30

    # Separator
    draw.line([(30, y), (WIDTH - 30, y)], fill=CARD_BORDER, width=2)
    y += 15

    # --- Tokens/sec comparison ---
    draw.text((30, y), "TOKENS / SEC", fill=TEXT_ACCENT, font=font_label)
    y += 30

    left_tps = metrics_left.get("tokens_per_sec", 0) if metrics_left else 0
    right_tps = metrics_right.get("tokens_per_sec", 0) if metrics_right else 0
    max_tps = max(left_tps, right_tps, 1)

    draw_bar(draw, 30, y, 250, 28, left_tps, max_tps, GREEN)
    draw_bar(draw, 328, y, 250, 28, right_tps, max_tps, BLUE)
    y += 35

    draw.text((30, y), f"{left_tps:.1f} tok/s", fill=GREEN, font=font_label)
    draw.text((328, y), f"{right_tps:.1f} tok/s", fill=BLUE, font=font_label)
    y += 35

    # --- Duration ---
    draw.text((30, y), "DURATION", fill=TEXT_ACCENT, font=font_label)
    y += 30

    left_dur = metrics_left.get("duration_sec", 0) if metrics_left else 0
    right_dur = metrics_right.get("duration_sec", 0) if metrics_right else 0
    max_dur = max(left_dur, right_dur, 1)

    draw_bar(draw, 30, y, 250, 28, left_dur, max_dur, ORANGE)
    draw_bar(draw, 328, y, 250, 28, right_dur, max_dur, PURPLE)
    y += 35

    draw.text((30, y), f"{left_dur:.1f}s", fill=ORANGE, font=font_label)
    draw.text((328, y), f"{right_dur:.1f}s", fill=PURPLE, font=font_label)
    y += 40

    # Separator
    draw.line([(30, y), (WIDTH - 30, y)], fill=CARD_BORDER, width=2)
    y += 15

    # --- Token Breakdown ---
    draw.text((30, y), "TOKEN BREAKDOWN", fill=TEXT_ACCENT, font=font_label)
    y += 30

    categories = [
        ("Input", "tokens_input", TEXT_WHITE),
        ("Output", "tokens_output", GREEN),
        ("Reasoning", "tokens_reasoning", ORANGE),
        ("Total", "tokens_total", TEXT_ACCENT),
    ]

    for cat_name, key, color in categories:
        left_val = metrics_left.get(key, 0) if metrics_left else 0
        right_val = metrics_right.get(key, 0) if metrics_right else 0
        max_val = max(left_val, right_val, 1)

        draw.text((30, y), cat_name, fill=TEXT_DIM, font=font_small)
        draw_bar(draw, 100, y, 200, 20, left_val, max_val, color)
        draw_bar(draw, 328, y, 200, 20, right_val, max_val, color)
        y += 25

        draw.text((100, y), f"{left_val:,}", fill=color, font=font_tiny)
        draw.text((328, y), f"{right_val:,}", fill=color, font=font_tiny)
        y += 20

    y += 10

    # --- Cost ---
    draw.text((30, y), "COST", fill=TEXT_ACCENT, font=font_label)
    y += 30

    left_cost = metrics_left.get("cost", 0) if metrics_left else 0
    right_cost = metrics_right.get("cost", 0) if metrics_right else 0
    max_cost = max(left_cost, right_cost, 0.0001)

    draw_bar(draw, 30, y, 250, 28, left_cost, max_cost, GREEN)
    draw_bar(draw, 328, y, 250, 28, right_cost, max_cost, BLUE)
    y += 35

    draw.text((30, y), f"${left_cost:.6f}", fill=GREEN, font=font_label)
    draw.text((328, y), f"${right_cost:.6f}", fill=BLUE, font=font_label)
    y += 40

    # Separator
    draw.line([(30, y), (WIDTH - 30, y)], fill=CARD_BORDER, width=2)
    y += 15

    # --- GPU Usage (from monitoring) ---
    draw.text((30, y), "GPU USAGE", fill=TEXT_ACCENT, font=font_label)
    y += 30

    if gpu_data:
        # Show GPU usage graph
        gpu_values = [row["gpu_percent"] for row in gpu_data[-60:]]  # Last 60 samples
        if gpu_values:
            graph_x = 30
            graph_y = y
            graph_w = WIDTH - 60
            graph_h = 80

            # Draw graph background
            draw_rounded_rect(draw, (graph_x, graph_y, graph_x + graph_w, graph_y + graph_h),
                            radius=4, fill=BAR_BG)

            # Draw graph line
            max_gpu = max(gpu_values) if max(gpu_values) > 0 else 1
            points = []
            for i, v in enumerate(gpu_values):
                px = graph_x + int(i * graph_w / max(len(gpu_values) - 1, 1))
                py = graph_y + graph_h - int(v / max_gpu * (graph_h - 10)) - 5
                points.append((px, py))

            if len(points) > 1:
                draw.line(points, fill=RED, width=2)

            # Current value
            current_gpu = gpu_values[-1] if gpu_values else 0
            draw.text((graph_x + graph_w - 80, graph_y + 5),
                     f"{current_gpu:.1f}%", fill=RED, font=font_label)

            y += graph_h + 10

            # VRAM
            vram_used = gpu_data[-1]["vram_used_mb"] if gpu_data else 0
            vram_total = gpu_data[-1]["vram_total_mb"] if gpu_data else 0
            draw.text((30, y), f"VRAM: {vram_used:.0f} / {vram_total:.0f} MB", fill=TEXT_DIM, font=font_label)
            y += 25

            # Clocks (convert MHz to GHz)
            mclk = gpu_data[-1]["mclk_ghz"] / 1000 if gpu_data else 0
            sclk = gpu_data[-1]["sclk_ghz"] / 1000 if gpu_data else 0
            draw.text((30, y), f"Memory: {mclk:.3f} GHz  |  Core: {sclk:.3f} GHz", fill=TEXT_DIM, font=font_small)
            y += 25

            # Note about GPU usage
            draw.text((30, y), "(API calls - no local GPU load)", fill=TEXT_DIM, font=font_tiny)
            y += 20
    else:
        draw.text((30, y), "Waiting for GPU data...", fill=TEXT_DIM, font=font_label)
        y += 30

    y += 15

    # --- Progress bar ---
    progress = frame_num / max(total_frames, 1)
    draw_rounded_rect(draw, (30, HEIGHT - 60, WIDTH - 30, HEIGHT - 40),
                     radius=5, fill=BAR_BG)
    bar_w = max(10, int((WIDTH - 60) * progress))
    draw_rounded_rect(draw, (30, HEIGHT - 60, 30 + bar_w, HEIGHT - 40),
                     radius=5, fill=TEXT_ACCENT)

    # Frame counter
    draw.text((WIDTH - 150, HEIGHT - 35), f"Frame {frame_num}/{total_frames}",
             fill=TEXT_DIM, font=font_small)

    return img


def main():
    if len(sys.argv) < 4:
        print("Usage: render_dashboard.py <metrics_left.json> <metrics_right.json> <gpu.csv> <output_dir> [total_frames]")
        sys.exit(1)

    metrics_left_file = sys.argv[1]
    metrics_right_file = sys.argv[2]
    gpu_csv_file = sys.argv[3]
    output_dir = sys.argv[4]
    total_frames = int(sys.argv[5]) if len(sys.argv) > 5 else 150  # 5 seconds at 30fps

    os.makedirs(output_dir, exist_ok=True)

    # Load metrics
    metrics_left = None
    if os.path.exists(metrics_left_file):
        with open(metrics_left_file) as f:
            metrics_left = json.load(f)

    metrics_right = None
    if os.path.exists(metrics_right_file):
        with open(metrics_right_file) as f:
            metrics_right = json.load(f)

    # Load GPU data
    gpu_data = []
    if os.path.exists(gpu_csv_file):
        with open(gpu_csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    gpu_data.append({
                        "timestamp": float(row["timestamp"]),
                        "gpu_percent": float(row["gpu_percent"]),
                        "vram_used_mb": float(row["vram_used_mb"]),
                        "vram_total_mb": float(row["vram_total_mb"]),
                        "mclk_ghz": float(row["mclk_ghz"]),
                        "sclk_ghz": float(row["sclk_ghz"]),
                    })
                except (ValueError, KeyError):
                    pass

    # Render frames
    for i in range(total_frames):
        img = render_frame(i, metrics_left, metrics_right, gpu_data, total_frames)
        img.save(os.path.join(output_dir, f"frame_{i:04d}.png"))
        if i % 30 == 0:
            print(f"Rendered frame {i}/{total_frames}")

    print(f"Done: {total_frames} frames in {output_dir}")


if __name__ == "__main__":
    main()
