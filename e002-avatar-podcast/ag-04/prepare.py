#!/usr/bin/env python3
"""Generate Godot config JSON and TikTok-style ASS subtitles."""
import json, math, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
TIMING = os.path.join(HERE, "../ag-03/timing.json")
CONFIG_OUT = os.path.join(HERE, "godot_project/config.json")
SUBS_OUT = os.path.join(HERE, "subtitles.ass")

with open(TIMING) as f:
    timing = json.load(f)

segments = []
cum = 0.0
for s in timing:
    segments.append({
        "segment": s["segment"],
        "speaker": s["speaker"],
        "text": s["text"],
        "start": round(cum, 3),
        "end": round(cum + s["duration"], 3),
    })
    cum += s["duration"]

duration = cum

# ── Godot config ──────────────────────────────────────────
godot_cfg = {
    "segments": [{"start": s["start"], "end": s["end"], "speaker": s["speaker"], "text": s["text"]} for s in segments],
    "duration": duration,
    "fps": 25,
    "w": 608,
    "h": 1080,
    "output_dir": os.path.join(HERE, "godot_project/frames"),
    "bg": os.path.join(HERE, "../ag-06/podcast_bg.png"),
    "avatar_a": os.path.join(HERE, "../ag-06/avatar_a.png"),
    "avatar_b": os.path.join(HERE, "../ag-06/avatar_b.png"),
}

os.makedirs(os.path.dirname(CONFIG_OUT), exist_ok=True)
with open(CONFIG_OUT, "w") as f:
    json.dump(godot_cfg, f, indent=2)
print(f"Config written: {CONFIG_OUT}")

# ── TikTok-style ASS subtitles ────────────────────────────
COLORS = ["&H00FFFFFF", "&H0000D7FF", "&H0088FF00", "&H006B6BFF", "&H00FFCB6B"]
COLOR_NAMES = ["#FFFFFF", "#FFD700", "#00FF88", "#FF6B6B", "#6BCBFF"]

def split_phrase(text):
    words = text.split()
    if len(words) <= 4:
        return [text]
    chunks = []
    i = 0
    while i < len(words):
        chunk_size = min(4, max(2, len(words) - i))
        if chunk_size < 2 and chunks:
            chunks[-1] += " " + words[i]
            i += 1
        else:
            chunks.append(" ".join(words[i:i+chunk_size]))
            i += chunk_size
    return chunks

ass_lines = []
ass_lines.append("[Script Info]")
ass_lines.append("Title: Podcast Subtitles")
ass_lines.append("ScriptType: v4.00+")
ass_lines.append("WrapStyle: 0")
ass_lines.append("ScaledBorderAndShadow: yes")
ass_lines.append("YCbCr Matrix: TV.601")
ass_lines.append("")
ass_lines.append("[V4+ Styles]")
ass_lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
style_line = "Style: TikTok,Arial,28,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,50,1"
ass_lines.append(style_line)
ass_lines.append("")
ass_lines.append("[Events]")
ass_lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

sub_idx = 0
color_idx = 0
sub_entries = []

for seg in segments:
    phrases = split_phrase(seg["text"])
    seg_dur = seg["end"] - seg["start"]
    phrase_dur = seg_dur / len(phrases)

    for p, phrase in enumerate(phrases):
        ps = seg["start"] + p * phrase_dur
        pe = ps + phrase_dur

        def fmt_ts(t):
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = t % 60
            return f"{h}:{m:02d}:{s:05.2f}"

        color = COLORS[color_idx % len(COLORS)]
        asm_start = fmt_ts(ps)
        asm_end = fmt_ts(pe)
        escaped = phrase.replace("{", "\\{").replace("}", "\\}")
        line = f"Dialogue: 0,{asm_start},{asm_end},TikTok,,0,0,0,,{{\\c{color}}}{escaped}"
        ass_lines.append(line)
        color_idx += 1

os.makedirs(os.path.dirname(SUBS_OUT), exist_ok=True)
with open(SUBS_OUT, "w") as f:
    f.write("\n".join(ass_lines) + "\n")
print(f"Subtitles written: {SUBS_OUT} ({color_idx} subtitle entries)")

# ── Summary ───────────────────────────────────────────────
print(f"\nTotal duration: {duration:.3f}s")
print(f"Total segments: {len(segments)}")
