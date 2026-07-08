#!/usr/bin/env python3
"""
Adaptive video generator for narration-based educational videos.

Takes any text, generates TTS+VTT, detects content types, creates
appropriate visuals, and composes a video with word-level highlighted subtitles.

Usage:
    python generate_video.py "Your narration text here." --title "Chapter 1" --output ch1.mp4
"""

import subprocess, os, sys, math, re, json, argparse
from xml.sax.saxutils import escape

OUT = os.environ.get("HF_VIDEO_OUT", "output")

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD = "DejaVu Sans Bold"
FONT_REG = "DejaVu Sans"
FONT_MONO = "DejaVu Sans Mono"
BG = "0x0d1117"
ACCENTS = ["#ff4444", "#4488ff", "#44cc88", "#ff8844", "#aa66ff"]

# --- Keyword-based content type detection ---
CONTENT_PATTERNS = {
    "code": [
        r'\bimport\b', r'\bsubscribe\b', r'\bscript\b', r'\bsdk\b', r'\bapi\b',
        r'\bfunction\b', r'\bcode\b', r'\bpython\b', r'\bterminal\b', r'\bcommand\b',
        r'\b>>>\b', r'\berror\b', r'\bnot_enough\b', r'\bfailed\b', r'\bcrash\b',
        r'\binstall\b', r'\bkey\b',
    ],
    "impact": [
        r'\bnot enough\b', r'\bno credits?\b', r'\bzero\b', r'\bnothing\b',
        r'\bfailed\b', r'\bblocked\b', r'\b160%\b', r'\bdollar\b', r'\bexpand\b',
        r'\bwrong\b', r'\bproblem\b', r'\bdetect\b',
    ],
    "lesson": [
        r'\blesson\b', r'\blearn\b', r'\bremember\b', r'\bcheck\b',
        r'\bverify\b', r'\balways\b', r'\bnever\b',
    ],
    "tool": [
        r'\bagent-browser\b', r'\bheadless\b', r'\bchrome\b', r'\bswiftshader\b',
        r'\breact\b', r'\bffmpeg\b', r'\bpython\b', r'\bcli\b',
    ],
}


def detect_content_type(text):
    """Detect visual type from text content."""
    scores = {}
    for ctype, patterns in CONTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
        if score:
            scores[ctype] = score
    if not scores:
        return "text"
    return max(scores, key=scores.get)


# --- VTT Parsing ---
def parse_vtt(path):
    """Parse VTT into phrase-level cues with timestamps."""
    with open(path) as f:
        content = f.read()
    lines = content.strip().split("\n")
    phrases = []
    for i, line in enumerate(lines):
        if "-->" in line:
            parts = line.split(" --> ")
            def ts(s):
                s = s.replace(",", ".")
                h, m, sec = s.split(":")
                return int(h) * 3600 + int(m) * 60 + float(sec)
            start = ts(parts[0].strip())
            end = ts(parts[1].strip())
            for j in range(i + 1, len(lines)):
                if lines[j].strip() and "-->" not in lines[j]:
                    phrases.append({
                        "text": lines[j].strip(),
                        "start": start,
                        "end": end,
                    })
                    break
    return phrases


# --- Adaptive chunk timing ---
def estimate_chunk_timing(phrases, chunk_size=3):
    """Group words into chunks of N words with flat timing division.
    
    Short chunks (3-5 words, ~0.5-2s) are more accurate than individual words
    because the flat division within a chunk has less relative error.
    """
    chunks = []
    for p in phrases:
        word_list = p["text"].split()
        phrase_dur = p["end"] - p["start"]
        total_chars = sum(len(w) for w in word_list)
        if total_chars == 0:
            continue
        char_time = phrase_dur / total_chars
        ws = p["start"]
        # Group into chunks of chunk_size words
        group = []
        group_chars = 0
        for w in word_list:
            group.append(w)
            group_chars += len(w)
            if len(group) >= chunk_size:
                wd = group_chars * char_time
                we = min(ws + wd, p["end"])
                chunks.append({"text": " ".join(group), "start": ws, "end": we, "phrase": p["text"]})
                ws = we
                group = []
                group_chars = 0
        
        # Remaining words
        if group:
            wd = group_chars * char_time
            we = min(ws + wd, p["end"])
            chunks.append({"text": " ".join(group), "start": ws, "end": we, "phrase": p["text"]})

    # Fix: ensure last chunk ends at phrase end
    if chunks and phrases:
        chunks[-1]["end"] = phrases[-1]["end"]
    return chunks


# --- Adaptive font sizing ---
def calc_font_size(phrases, width=608):
    """Calculate optimal font size based on longest phrase."""
    max_len = max(len(p["text"]) for p in phrases)
    # At width=608 with wrapping, font 48 fits ~20 chars/line, ~40 chars in 2 lines
    # For any text, use minimum 36 (readable) and let ASS wrap long lines
    font_size = max(36, min(56, int(56 * 25 / max_len)))
    return font_size


# --- Visual segment generation ---
def build_visual_segments(phrases, title="Chapter"):
    """Group phrases into visual segments based on content type and timing."""
    segments = []
    current_type = None
    current_phrases = []
    current_dur = 0
    total_dur = phrases[-1]["end"] if phrases else 0

    for p in phrases:
        ptype = detect_content_type(p["text"])
        pdur = p["end"] - p["start"]

        # Start new segment on type change or every ~8s for pattern interrupt
        if ptype != current_type or current_dur > 7.0:
            if current_phrases:
                segments.append({
                    "type": current_type,
                    "phrases": current_phrases,
                    "duration": current_dur,
                })
            current_type = ptype
            current_phrases = [p]
            current_dur = pdur
        else:
            current_phrases.append(p)
            current_dur += pdur

    if current_phrases:
        segments.append({
            "type": current_type,
            "phrases": current_phrases,
            "duration": current_dur,
        })

    # First segment always "title" type
    if segments:
        segments[0]["type"] = "title"
        segments[0]["title_text"] = title
    # Last segment always "lesson" type
    if len(segments) > 1:
        segments[-1]["type"] = "lesson"

    return segments


def render_visual(seg, sd, accent, outpath):
    """Render a single visual segment with ffmpeg drawtext."""
    stype = seg["type"]

    if stype == "title":
        title = seg.get("title_text", "Chapter")
        filt = (
            f"color=c={BG}:s=608x1080:d={sd}:r=24[s0];"
            f"[s0]drawbox=0:0:608:3:color={accent}:t=fill[s1];"
            f"[s1]drawtext=text='{title}':fontsize=48:fontcolor=white:"
            f"x=(w-text_w)/2:y=h*0.25:fontfile={FONT_B}[outv]"
        )
    elif stype == "code":
        # Show code-like representation
        text = seg["phrases"][0]["text"] if seg["phrases"] else ""
        filt = (
            f"color=c={BG}:s=608x1080:d={sd}:r=24[s0];"
            f"[s0]drawbox=40:150:530:200:color=#161b22:t=fill[s1];"
            f"[s1]drawtext=text='{text}':fontsize=18:fontcolor=#88cc88:"
            f"x=50:y=200:fontfile={FONT_M}:fix_bounds=true[outv]"
        )
    elif stype == "impact":
        text = seg["phrases"][0]["text"] if seg["phrases"] else ""
        # Find key impact words
        words = text.split()
        impact_words = [w for w in words if len(w) > 3][:3] or words[:3]
        impact_text = " ".join(impact_words)
        filt = (
            f"color=c={BG}:s=608x1080:d={sd}:r=24[s0];"
            f"[s0]drawtext=text='{impact_text}':fontsize=64:fontcolor={accent}:"
            f"x=(w-text_w)/2:y=h*0.3:fontfile={FONT_B}[outv]"
        )
    elif stype == "lesson":
        text = seg["phrases"][0]["text"] if seg["phrases"] else ""
        filt = (
            f"color=c={BG}:s=608x1080:d={sd}:r=24[s0];"
            f"[s0]drawbox=0:0:608:3:color={accent}:t=fill[s1];"
            f"[s1]drawtext=text='Key lesson':fontsize=18:fontcolor={accent}:"
            f"x=30:y=50:fontfile={FONT_B}[s2];"
            f"[s2]drawtext=text='{text}':fontsize=36:fontcolor=white:"
            f"x=(w-text_w)/2:y=h*0.3:fontfile={FONT_B}[outv]"
        )
    else:  # text
        text = seg["phrases"][0]["text"] if seg["phrases"] else ""
        filt = (
            f"color=c={BG}:s=608x1080:d={sd}:r=24[s0];"
            f"[s0]drawtext=text='{text}':fontsize=32:fontcolor=#e6e6e6:"
            f"x=(w-text_w)/2:y=h*0.3:fontfile={FONT_R}:fix_bounds=true[outv]"
        )

    subprocess.run(["ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={BG}:s=608x1080:d={sd}:r=24",
        "-filter_complex", filt, "-map", "[outv]",
        "-c:v", "libx264", "-b:v", "1500k", "-an", outpath],
        check=True, capture_output=True)


# --- ASS subtitle generation ---
def generate_ass(chunks, font_size=48, ass_path="subtitles.ass"):
    """Generate ASS with per-chunk highlighting (current chunk yellow).
    
    Each chunk is 2-4 words. The full phrase is shown with the current chunk
    highlighted in yellow, past chunks in gray, future chunks in white.
    """
    YELLOW = "{\\c&H00CCFF&}"
    WHITE = "{\\c&HFFFFFF&}"
    GRAY = "{\\c&H888888&}"

    with open(ass_path, "w") as f:
        f.write("[Script Info]\nScriptType: v4.00+\n")
        f.write("PlayResX: 608\nPlayResY: 1080\n")
        f.write("ScaledBorderAndShadow: yes\n\n")
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, ")
        f.write("OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ")
        f.write("ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, ")
        f.write("Alignment, MarginL, MarginR, MarginV, Encoding\n")
        f.write(f"Style: Default,{FONT_BOLD},{font_size},")
        f.write("&H00FFFFFF,&H0000FF00,&H00000000,&H00000000,")
        f.write("0,0,0,0,100,100,0,0,1,1,0,2,40,40,60,1\n\n")
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

        # Group by phrase
        phrase_groups = {}
        for c in chunks:
            phrase_groups.setdefault(c["phrase"], []).append(c)

        for phrase_text, group in phrase_groups.items():
            phrase_words = phrase_text.split()
            # Build word-to-chunk mapping
            chunk_word_counts = [len(c["text"].split()) for c in group]
            
            for i, ch in enumerate(group):
                # Determine word boundaries for this chunk
                words_before = sum(chunk_word_counts[:i])
                words_up_to = words_before + chunk_word_counts[i]
                
                parts = []
                for j, w in enumerate(phrase_words):
                    if j < words_before:
                        parts.append(f"{GRAY}{w}{WHITE}")
                    elif j < words_up_to:
                        parts.append(f"{YELLOW}{w}{WHITE}")
                    else:
                        parts.append(w)

                line = " ".join(parts)
                def ts(sec):
                    h = int(sec // 3600)
                    m = int(sec % 3600 // 60)
                    s = sec % 60
                    cs = int((s - int(s)) * 100)  # centiseconds
                    return f"{h:01d}:{m:02d}:{int(s):02d}.{cs:02d}"
                f.write(f"Dialogue: 0,{ts(ch['start'])},{ts(ch['end'])},Default,,0,0,0,,{line}\n")


# --- Main pipeline ---
def generate_video(text, title="Chapter", output="output/video.mp4", voice="en-US-JennyNeural"):
    """Full adaptive video generation pipeline."""
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    base = output.replace(".mp4", "")

    # 1. TTS + VTT
    print("1. Generating TTS...")
    subprocess.run(["edge-tts", "--voice", voice, "-t", text,
        "--write-media", f"{base}.mp3", "--write-subtitles", f"{base}.vtt"],
        timeout=60, capture_output=True)

    # 2. Parse VTT
    phrases = parse_vtt(f"{base}.vtt")
    if not phrases:
        print("ERROR: No phrases parsed")
        return False
    print(f"   {len(phrases)} phrases, {phrases[-1]['end']:.1f}s total")

    # 3. Chunk timing (groups of 3 words for accuracy)
    chunks = estimate_chunk_timing(phrases, chunk_size=3)
    print(f"   {len(chunks)} chunks from {sum(len(p['text'].split()) for p in phrases)} words")

    # 4. Adaptive font size
    font_size = calc_font_size(phrases)
    print(f"   Font size: {font_size}")

    # 5. Generate ASS
    ass_path = f"{base}.ass"
    generate_ass(chunks, font_size, ass_path)
    print(f"   ASS subtitles: {ass_path}")

    # 6. Visual segments
    segments = build_visual_segments(phrases, title)
    print(f"   {len(segments)} visual segments")

    # 6. Render visuals
    print("2. Rendering visuals...")
    seg_files = []
    for i, seg in enumerate(segments):
        out = f"{base}_vis_{i}.mp4"
        seg_files.append(out)
        accent = ACCENTS[i % len(ACCENTS)]
        render_visual(seg, seg["duration"], accent, out)
        print(f"   {i}: {seg['type']} ({seg['duration']:.1f}s)")

    # 7. Concatenate visuals
    concat_dir = os.path.dirname(os.path.abspath(base)) or "."
    with open(f"{base}_concat.txt", "w") as f:
        for sf in seg_files:
            f.write(f"file '{os.path.abspath(sf)}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", f"{base}_concat.txt", "-c", "copy", f"{base}_visuals.mp4"],
        check=True, capture_output=True)

    # 7. Burn subtitles
    subprocess.run(["ffmpeg", "-y",
        "-i", f"{base}_visuals.mp4",
        "-filter_complex", f"subtitles={ass_path}[outv]",
        "-map", "[outv]", "-c:v", "libx264", "-b:v", "1500k",
        "-an", f"{base}_sub.mp4"], check=True, capture_output=True)

    # 8. Add audio
    subprocess.run(["ffmpeg", "-y",
        "-i", f"{base}_sub.mp4", "-i", f"{base}.mp3",
        "-c:v", "copy", "-c:a", "aac",
        "-map", "0:v", "-map", "1:a", "-shortest", output],
        check=True, capture_output=True)

    # Cleanup
    for f in seg_files:
        os.remove(f)
    for f in [f"{base}_concat.txt", f"{base}_visuals.mp4", f"{base}_sub.mp4"]:
        if os.path.exists(f):
            os.remove(f)

    size = os.path.getsize(output)
    print(f"\nDone: {output} ({size/1024:.0f}KB)")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adaptive educational video generator")
    parser.add_argument("text", nargs="?", help="Narration text")
    parser.add_argument("--title", default="Chapter", help="Chapter title")
    parser.add_argument("--output", default="output/video.mp4", help="Output path")
    parser.add_argument("--voice", default="en-US-JennyNeural", help="TTS voice")
    args = parser.parse_args()

    text = args.text or sys.stdin.read().strip()
    if not text:
        print("Usage: python generate_video.py 'text' --title 'Title' --output out.mp4")
        sys.exit(1)

    generate_video(text, args.title, args.output, args.voice)
