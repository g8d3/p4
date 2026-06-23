#!/usr/bin/env python3
"""Build the TTS/ASR demo video with real Xiaomi API output."""
import math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 608, 1080
FPS = 15
BASE = "/home/vuos/code/p4/e010-more-videos/ag-03"
FRAMES_DIR = f"{BASE}/assets/frames"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# Colors
BG = (16, 16, 28)
TITLE_C = (100, 200, 255)
CMD_C = (100, 255, 100)
OUT_C = (220, 220, 220)
ACCENT_C = (255, 200, 100)
DIM_C = (120, 120, 140)
GREEN_C = (100, 255, 100)
BAR_C = (80, 200, 80)

def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)

def base():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # Top bar
    d.rectangle([0, 0, W, 50], fill=(30, 30, 50))
    for i, c in enumerate([(220, 80, 80), (220, 180, 80), (80, 200, 80)]):
        cx = 20 + i * 30
        d.ellipse([cx, 18, cx+14, 32], fill=c)
    d.text((W//2, 25), "xiaomi-mimo-api — demo", fill=(140, 140, 160), font=font(16), anchor="mm")
    # Bottom bar
    d.rectangle([0, H-40, W, H], fill=(30, 30, 50))
    d.text((W//2, H-20), "Xiaomi MIMO  ·  TTS + ASR", fill=(100, 100, 130), font=font(13), anchor="mm")
    return img, d

def save(img, i):
    img.save(f"{FRAMES_DIR}/frame_{i:05d}.png")

def scene_title(n):
    frames = []
    for f in range(n):
        img, d = base()
        d.text((W//2, 300), "Xiaomi MIMO", fill=TITLE_C, font=font(36), anchor="mm")
        d.text((W//2, 360), "TTS & ASR", fill=ACCENT_C, font=font(28), anchor="mm")
        d.text((W//2, 420), "Text to Speech  ·  Speech to Text", fill=DIM_C, font=font(20), anchor="mm")
        d.rounded_rectangle([W//2-130, 480, W//2+130, 520], radius=8, fill=(40, 40, 70))
        d.text((W//2, 500), "mimo-v2.5-tts  +  mimo-v2.5-asr", fill=(120, 180, 255), font=font(14), anchor="mm")
        frames.append(img)
    return frames

def type_text(d, lines, y_start=80, x=25, line_h=28, cursor=True, visible_chars=9999):
    y = y_start
    for line in lines:
        if isinstance(line, dict):
            text, color, f = line["text"], line.get("color", OUT_C), line.get("font", font(15, bold=False))
        else:
            text, color, f = line, OUT_C, font(15, bold=False)
        prev_remaining = visible_chars
        visible_chars -= len(text)
        if prev_remaining <= 0:
            break
        show = text[:prev_remaining]
        if cursor and prev_remaining < len(text):
            show += "\u2588"
        d.text((x, y), show, fill=color, font=f)
        y += line_h
    return y

def scene_tts_cmd(n):
    lines = [
        {"text": "$ xiaomi-api tts \\", "color": CMD_C},
        {"text": "    --text \"Hola, soy Salome", "color": CMD_C},
        {"text": "      desde la API de Xiaomi MIMO.", "color": CMD_C},
        {"text": "      Voz generada con IA.\"", "color": CMD_C},
        {"text": "    --voice Mia \\", "color": CMD_C},
        {"text": "    --format wav \\", "color": CMD_C},
        {"text": "    -o tts_xiaomi.wav", "color": CMD_C},
        {"text": "", "color": CMD_C},
        {"text": "[POST] /v1/chat/completions", "color": DIM_C, "font": font(13, False)},
        {"text": "model: mimo-v2.5-tts", "color": DIM_C, "font": font(13, False)},
        {"text": "modalities: [audio]", "color": DIM_C, "font": font(13, False)},
        {"text": "voice: Mia  format: wav", "color": DIM_C, "font": font(13, False)},
    ]
    total_chars = sum(len(l.get("text", l) if isinstance(l, dict) else l) for l in lines)
    chars_per_frame = max(1, total_chars // (n - 2))
    frames = []
    for f in range(n):
        img, d = base()
        type_text(d, lines, visible_chars=chars_per_frame * f)
        frames.append(img)
    return frames

def scene_tts_result(n):
    frames = []
    for f in range(n):
        img, d = base()
        lines = [
            {"text": "$ xiaomi-api tts ...", "color": CMD_C},
            {"text": "", "color": OUT_C},
            {"text": "Audio guardado: tts_xiaomi.wav", "color": ACCENT_C},
            {"text": "Size: 384,044 bytes (375 KB)", "color": OUT_C},
            {"text": "Duration: 8.00 seconds", "color": OUT_C},
            {"text": "Format: WAV 24kHz mono", "color": OUT_C},
            {"text": "", "color": OUT_C},
            {"text": "\u266A Playing audio...", "color": TITLE_C, "font": font(18)},
        ]
        y = 80
        for line in lines:
            text = line["text"]
            color = line.get("color", OUT_C)
            fnt = line.get("font", font(15))
            d.text((25, y), text, fill=color, font=fnt)
            y += 30
        # Waveform
        bar_y, bar_h, num_bars = 420, 200, 30
        for i in range(num_bars):
            phase = f * 0.3 + i * 0.4
            h = int(40 + 80 * abs(math.sin(phase)) * (1 - i / num_bars * 0.5))
            bx = 30 + i * 18
            cv = int(80 + 120 * abs(math.sin(phase)))
            d.rectangle([bx, bar_y + bar_h - h, bx + 12, bar_y + bar_h], fill=(cv, 200, cv))
        d.text((W//2, bar_y + bar_h + 20), "TTS Audio Output", fill=DIM_C, font=font(13), anchor="mm")
        frames.append(img)
    return frames

def scene_tts_play(n):
    frames = []
    for f in range(n):
        img, d = base()
        d.text((W//2, 350), "\u25B6  Now playing:", fill=DIM_C, font=font(18), anchor="mm")
        d.text((W//2, 410), "tts_xiaomi.wav", fill=ACCENT_C, font=font(22), anchor="mm")
        d.text((W//2, 460), "8.0s  ·  375 KB  ·  WAV", fill=DIM_C, font=font(16), anchor="mm")
        # Animated bars
        bar_y = 530
        num_bars = 40
        for i in range(num_bars):
            phase = f * 0.4 + i * 0.3
            h = int(20 + 60 * abs(math.sin(phase)))
            bx = 30 + i * 14
            cv = int(100 + 155 * abs(math.sin(phase)))
            d.rectangle([bx, bar_y + 100 - h, bx + 10, bar_y + 100], fill=(cv, 200, cv))
        d.text((W//2, bar_y + 130), "Xiaomi MIMO TTS", fill=TITLE_C, font=font(14), anchor="mm")
        frames.append(img)
    return frames

def scene_asr_cmd(n):
    lines = [
        {"text": "$ xiaomi-api asr \\", "color": CMD_C},
        {"text": "    --audio tts_xiaomi.wav", "color": CMD_C},
        {"text": "", "color": OUT_C},
        {"text": "[POST] /v1/chat/completions", "color": DIM_C, "font": font(13, False)},
        {"text": "model: mimo-v2.5-asr", "color": DIM_C, "font": font(13, False)},
        {"text": "input: tts_xiaomi.wav (base64)", "color": DIM_C, "font": font(13, False)},
        {"text": "", "color": OUT_C},
        {"text": "Analyzing audio...", "color": TITLE_C},
    ]
    total_chars = sum(len(l.get("text", l) if isinstance(l, dict) else l) for l in lines)
    chars_per_frame = max(1, total_chars // (n - 2))
    frames = []
    for f in range(n):
        img, d = base()
        type_text(d, lines, visible_chars=chars_per_frame * f)
        frames.append(img)
    return frames

def scene_asr_result(n):
    transcribed = "Hola, soy Salame de la API de Xiaomi Mimo. Pues, tiene ada conemidensiosi artificial?"
    frames = []
    for f in range(n):
        img, d = base()
        y = 80
        d.text((25, y), "$ xiaomi-api asr --audio tts_xiaomi.wav", fill=CMD_C, font=font(15)); y += 35
        d.text((25, y), "", fill=OUT_C, font=font(15)); y += 30
        d.text((25, y), "Transcription:", fill=ACCENT_C, font=font(18)); y += 35
        # Box
        box_y = y + 10
        d.rounded_rectangle([20, box_y, W-20, box_y+140], radius=10, fill=(25, 35, 50))
        # Word wrap
        words = transcribed.split()
        wrapped, cur = [], ""
        for word in words:
            test = cur + " " + word if cur else word
            bbox = d.textbbox((0,0), test, font=font(16))
            if bbox[2] - bbox[0] > W - 60:
                wrapped.append(cur)
                cur = word
            else:
                cur = test
        if cur:
            wrapped.append(cur)
        visible = int(len(wrapped) * min(1.0, f / max(1, n * 0.5)))
        ty = box_y + 15
        for i, lt in enumerate(wrapped[:visible+1]):
            d.text((35, ty), lt, fill=(200, 255, 200), font=font(16))
            ty += 25
        y_end = box_y + 160
        d.text((25, y_end), "ASR recognized the speech!", fill=GREEN_C, font=font(15))
        d.text((25, y_end+30), "TTS + ASR = complete voice pipeline", fill=ACCENT_C, font=font(15))
        frames.append(img)
    return frames

def scene_outro(n):
    frames = []
    for f in range(n):
        img, d = base()
        d.text((W//2, 380), "Xiaomi MIMO API", fill=TITLE_C, font=font(32), anchor="mm")
        d.text((W//2, 440), "TTS + ASR = Voice AI", fill=ACCENT_C, font=font(24), anchor="mm")
        d.text((W//2, 520), "Free API  ·  Fast  ·  Multi-language", fill=DIM_C, font=font(16), anchor="mm")
        d.text((W//2, 580), "token-plan-sgp.xiaomimimo.com", fill=(80, 80, 110), font=font(13), anchor="mm")
        frames.append(img)
    return frames

def main():
    os.makedirs(FRAMES_DIR, exist_ok=True)
    for f in os.listdir(FRAMES_DIR):
        os.remove(os.path.join(FRAMES_DIR, f))

    idx = 0
    scenes = [
        ("title", scene_title, int(6.5 * FPS)),
        ("tts_cmd", scene_tts_cmd, int(11 * FPS)),
        ("tts_result", scene_tts_result, int(8 * FPS)),
        ("tts_play", scene_tts_play, int(8 * FPS)),
        ("asr_cmd", scene_asr_cmd, int(5.5 * FPS)),
        ("asr_result", scene_asr_result, int(7 * FPS)),
        ("outro", scene_outro, int(6 * FPS)),
    ]
    total = sum(n for _, _, n in scenes)
    print(f"Generating {total} frames across {len(scenes)} scenes...")
    for name, func, nf in scenes:
        print(f"  Scene: {name} ({nf} frames)")
        for img in func(nf):
            save(img, idx)
            idx += 1
    print(f"Done: {idx} frames ({idx/FPS:.1f}s at {FPS}fps)")

if __name__ == "__main__":
    main()
