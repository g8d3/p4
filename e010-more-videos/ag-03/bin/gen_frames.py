#!/usr/bin/env python3
"""Generate terminal-style frames for TTS/ASR demo video (608x1080 vertical)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 608, 1080
FPS = 15
BG_COLOR = (16, 16, 28)
TITLE_COLOR = (100, 200, 255)
CMD_COLOR = (100, 255, 100)
OUTPUT_COLOR = (220, 220, 220)
ACCENT_COLOR = (255, 200, 100)
DIM_COLOR = (120, 120, 140)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

def load_font(size, bold=True):
    path = FONT_PATH if bold else FONT_REG
    return ImageFont.truetype(path, size)

def make_base():
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    # Subtle top bar
    draw.rectangle([0, 0, W, 50], fill=(30, 30, 50))
    for i, c in enumerate([(220, 80, 80), (220, 180, 80), (80, 200, 80)]):
        cx = 20 + i * 30
        draw.ellipse([cx, 18, cx+14, 32], fill=c)
    title_font = load_font(16)
    draw.text((W//2, 25), "xiaomi-mimo-api — demo", fill=(140, 140, 160),
              font=title_font, anchor="mm")
    # Bottom bar
    draw.rectangle([0, H-40, W, H], fill=(30, 30, 50))
    draw.text((W//2, H-20), "Xiaomi MIMO  ·  TTS + ASR", fill=(100, 100, 130),
              font=load_font(13), anchor="mm")
    return img, draw

def text_lines(draw, lines, y_start=80, line_h=28, x=25):
    y = y_start
    for line in lines:
        if isinstance(line, dict):
            text = line["text"]
            color = line.get("color", OUTPUT_COLOR)
            font = line.get("font", load_font(16, bold=False))
            draw.text((x, y), text, fill=color, font=font)
        else:
            draw.text((x, y), line, fill=OUTPUT_COLOR, font=load_font(16, bold=False))
        y += line_h
    return y

def frame_path(i):
    return f"/home/vuos/code/p4/e010-more-videos/ag-03/assets/frames/frame_{i:05d}.png"

def save_frame(img, i):
    img.save(frame_path(i))

def type_effect(base_func, full_lines, num_frames, start_frame, cursor_char="\u2588"):
    """Generate typing frames. base_func returns (img, draw) template."""
    frames = []
    total_chars = sum(len(l.get("text", l) if isinstance(l, dict) else l) for l in full_lines)
    chars_per_frame = max(1, total_chars // (num_frames - 2))  # leave 2 frames for full display

    for f in range(num_frames):
        img, draw = base_func()
        visible_chars = chars_per_frame * f
        y = 80
        line_h = 30
        for line in full_lines:
            if isinstance(line, dict):
                text = line["text"]
                color = line.get("color", OUTPUT_COLOR)
                font = line.get("font", load_font(16, bold=False))
                lh = line.get("line_h", line_h)
            else:
                text = line
                color = OUTPUT_COLOR
                font = load_font(16, bold=False)
                lh = line_h

            if visible_chars <= 0:
                break
            show = text[:visible_chars]
            # Add cursor on last visible line
            if visible_chars < len(text):
                show = show + cursor_char
            draw.text((25, y), show, fill=color, font=font)
            visible_chars -= len(text)
            y += lh
        frames.append(img)
    return frames

def scene_title(num_frames):
    """Title scene."""
    frames = []
    for f in range(num_frames):
        img, draw = make_base()
        # Fade in effect
        alpha = min(1.0, f / (num_frames * 0.4))
        big_font = load_font(36)
        sub_font = load_font(20)
        # Main title
        y = 300
        draw.text((W//2, y), "Xiaomi MIMO", fill=TITLE_COLOR, font=big_font, anchor="mm")
        y += 50
        draw.text((W//2, y), "TTS & ASR", fill=ACCENT_COLOR, font=load_font(28), anchor="mm")
        y += 60
        draw.text((W//2, y), "Text to Speech  ·  Speech to Text",
                  fill=DIM_COLOR, font=sub_font, anchor="mm")
        y += 80
        # API badge
        draw.rounded_rectangle([W//2-120, y, W//2+120, y+40], radius=8,
                               fill=(40, 40, 70))
        draw.text((W//2, y+20), "mimo-v2.5-tts  +  mimo-v2.5-asr",
                  fill=(120, 180, 255), font=load_font(14), anchor="mm")
        frames.append(img)
    return frames

def scene_tts_cmd(num_frames):
    """Show TTS command with typing effect."""
    lines = [
        {"text": "$ xiaomi-api tts \\", "color": CMD_COLOR, "font": load_font(15)},
        {"text": "    --text \"Hola, soy Salome", "color": CMD_COLOR, "font": load_font(15)},
        {"text": "      desde la API de Xiaomi MIMO.", "color": CMD_COLOR, "font": load_font(15)},
        {"text": "      Voz generada con IA.\"", "color": CMD_COLOR, "font": load_font(15)},
        {"text": "    --voice Mia \\", "color": CMD_COLOR, "font": load_font(15)},
        {"text": "    --format wav \\", "color": CMD_COLOR, "font": load_font(15)},
        {"text": "    -o tts_demo.wav", "color": CMD_COLOR, "font": load_font(15)},
        {"text": "", "color": CMD_COLOR, "font": load_font(15)},
        {"text": "[POST] /v1/chat/completions", "color": DIM_COLOR, "font": load_font(13)},
        {"text": "model: mimo-v2.5-tts", "color": DIM_COLOR, "font": load_font(13)},
        {"text": "modalities: [audio]", "color": DIM_COLOR, "font": load_font(13)},
        {"text": "voice: Mia  format: wav", "color": DIM_COLOR, "font": load_font(13)},
    ]
    return type_effect(make_base, lines, num_frames, 0)

def scene_tts_result(num_frames):
    """Show TTS result."""
    frames = []
    for f in range(num_frames):
        img, draw = make_base()
        lines = [
            {"text": "$ xiaomi-api tts ...", "color": CMD_COLOR, "font": load_font(15)},
            {"text": "", "font": load_font(15)},
            {"text": "Audio guardado: tts_demo.wav", "color": ACCENT_COLOR, "font": load_font(16)},
            {"text": "Size: 368,684 bytes (360 KB)", "color": OUTPUT_COLOR, "font": load_font(15)},
            {"text": "Duration: 7.68 seconds", "color": OUTPUT_COLOR, "font": load_font(15)},
            {"text": "Format: WAV 24kHz mono", "color": OUTPUT_COLOR, "font": load_font(15)},
            {"text": "", "font": load_font(15)},
            {"text": "\u266A Playing audio...", "color": (100, 200, 255), "font": load_font(18)},
        ]
        y = 80
        for line in lines:
            text = line["text"]
            color = line.get("color", OUTPUT_COLOR)
            font = line.get("font", load_font(15))
            draw.text((25, y), text, fill=color, font=font)
            y += 30

        # Visual waveform bar animation
        bar_y = 420
        bar_h = 200
        num_bars = 30
        import math
        for i in range(num_bars):
            phase = f * 0.3 + i * 0.4
            h = int(40 + 80 * abs(math.sin(phase)) * (1 - i / num_bars * 0.5))
            bx = 30 + i * 18
            color_val = int(80 + 120 * abs(math.sin(phase)))
            draw.rectangle([bx, bar_y + bar_h - h, bx + 12, bar_y + bar_h],
                          fill=(color_val, 200, color_val))
        draw.text((W//2, bar_y + bar_h + 20), "TTS Audio Output",
                  fill=DIM_COLOR, font=load_font(13), anchor="mm")
        frames.append(img)
    return frames

def scene_asr_cmd(num_frames):
    """Show ASR command with typing effect."""
    lines = [
        {"text": "$ xiaomi-api asr \\", "color": CMD_COLOR, "font": load_font(15)},
        {"text": "    --audio tts_demo.wav", "color": CMD_COLOR, "font": load_font(15)},
        {"text": "", "font": load_font(15)},
        {"text": "[POST] /v1/chat/completions", "color": DIM_COLOR, "font": load_font(13)},
        {"text": "model: mimo-v2.5-asr", "color": DIM_COLOR, "font": load_font(13)},
        {"text": "input: tts_demo.wav (base64)", "color": DIM_COLOR, "font": load_font(13)},
        {"text": "", "font": load_font(15)},
        {"text": "Analyzing audio...", "color": (100, 200, 255), "font": load_font(16)},
    ]
    return type_effect(make_base, lines, num_frames, 0)

def scene_asr_result(num_frames):
    """Show ASR transcription result."""
    frames = []
    for f in range(num_frames):
        img, draw = make_base()
        lines = [
            {"text": "$ xiaomi-api asr --audio tts_demo.wav", "color": CMD_COLOR, "font": load_font(15)},
            {"text": "", "font": load_font(15)},
            {"text": "Transcription:", "color": ACCENT_COLOR, "font": load_font(18)},
            {"text": "", "font": load_font(15)},
        ]
        y = 80
        for line in lines:
            text = line["text"]
            color = line.get("color", OUTPUT_COLOR)
            font = line.get("font", load_font(15))
            draw.text((25, y), text, fill=color, font=font)
            y += 30

        # Transcribed text in a box
        box_y = y + 10
        trans_text = "Hola, soy Salome desde la API de Xiaomi MIMO. Voz generada con IA."
        draw.rounded_rectangle([20, box_y, W-20, box_y+120], radius=10,
                              fill=(25, 35, 50))
        # Word wrap
        words = trans_text.split()
        lines_text = []
        current = ""
        max_w = W - 60
        trans_font = load_font(16)
        temp_draw = ImageDraw.Draw(img)
        for word in words:
            test = current + " " + word if current else word
            bbox = temp_draw.textbbox((0,0), test, font=trans_font)
            if bbox[2] - bbox[0] > max_w:
                lines_text.append(current)
                current = word
            else:
                current = test
        if current:
            lines_text.append(current)

        ty = box_y + 15
        visible_words = int(len(lines_text) * min(1.0, f / max(1, num_frames * 0.5)))
        for i, lt in enumerate(lines_text[:visible_words+1]):
            draw.text((35, ty), lt, fill=(200, 255, 200), font=trans_font)
            ty += 25

        y_end = box_y + 140
        draw.text((25, y_end), "ASR recognized the speech correctly!",
                  fill=(100, 255, 100), font=load_font(15))
        draw.text((25, y_end + 30), "TTS + ASR = complete voice pipeline",
                  fill=ACCENT_COLOR, font=load_font(15))
        frames.append(img)
    return frames

def scene_outro(num_frames):
    """Outro scene."""
    frames = []
    for f in range(num_frames):
        img, draw = make_base()
        big_font = load_font(32)
        draw.text((W//2, 400), "Xiaomi MIMO API", fill=TITLE_COLOR,
                  font=big_font, anchor="mm")
        draw.text((W//2, 460), "TTS + ASR = Voice AI", fill=ACCENT_COLOR,
                  font=load_font(24), anchor="mm")
        draw.text((W//2, 540), "Free API  ·  Fast  ·  Multi-language",
                  fill=DIM_COLOR, font=load_font(16), anchor="mm")
        draw.text((W//2, 620), "token-plan-sgp.xiaomimimo.com",
                  fill=(80, 80, 110), font=load_font(13), anchor="mm")
        frames.append(img)
    return frames

def main():
    out_dir = "/home/vuos/code/p4/e010-more-videos/ag-03/assets/frames"
    os.makedirs(out_dir, exist_ok=True)
    # Clear old frames
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))

    frame_idx = 0
    scenes = [
        ("title", scene_title, int(6.5 * FPS)),      # 6.5s — intro narration
        ("tts_cmd", scene_tts_cmd, int(11 * FPS)),   # 11s — "Usamos el modelo..."
        ("tts_result", scene_tts_result, int(17.5 * FPS)),  # 17.5s — TTS audio + comment
        ("asr_cmd", scene_asr_cmd, int(5.5 * FPS)),  # 5.5s — "Ahora reconocimiento..."
        ("asr_result", scene_asr_result, int(7 * FPS)),  # 7s — transcription
        ("outro", scene_outro, int(6 * FPS)),        # 6s — "Dos APIs..."
    ]
    total = sum(n for _, _, n in scenes)
    print(f"Generating {total} frames across {len(scenes)} scenes...")
    for name, func, nf in scenes:
        print(f"  Scene: {name} ({nf} frames)")
        frames = func(nf)
        for img in frames:
            save_frame(img, frame_idx)
            frame_idx += 1
    print(f"Done: {frame_idx} frames saved to {out_dir}")
    print(f"Total duration: {frame_idx / FPS:.1f}s at {FPS}fps")

if __name__ == "__main__":
    main()
