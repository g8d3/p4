#!/usr/bin/env python3
"""Generate all video variations from the extracted conversation.

Usage:
  ./generate_videos.py          # generates all compositions
  ./generate_videos.py talking-head  # generates single composition

Requires: remotion (npm), edge-tts (pip), ffmpeg
"""

import subprocess, sys, json, time, os, glob, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUTPUT = ROOT / "output"
TTS_DIR = OUTPUT / "tts"
TTS_DIR = OUTPUT / "tts"

COMPOSITIONS = {
    "talking-head": "Talking head explaining the debugging journey. Duration: ~30s",
    "podcast": "Two-hosts podcast discussing the engineering lessons. Duration: ~45s",
    "code-review": "Before/after comparison of approaches. Duration: ~25s",
    "timeline": "Animated timeline of events from the session. Duration: ~20s",
}

NARRATION_SCRIPTS = {
    "talking-head": [
        "We needed to extract conversation text from a Gemini share URL. Simple task, right?",
        "curl got the HTML in one second. But the conversation wasn't there. It was a JavaScript app.",
        "So we tried Chrome's dump-dom flag. It worked... but took thirty seconds.",
        "Eighty-eight percent of that time was pure waste. Waiting for a SPA to finish its background timers.",
        "The fix was sitting in our toolbox the whole time. Agent browser. Three point five seconds.",
        "The lesson? Always check what tools already exist before building from scratch.",
        "And when something takes thirty seconds... maybe stop and think before running more commands.",
    ],
    "podcast": [
        "Did you see what happened yesterday?",
        "You mean the Gemini extraction debacle?",
        "Exactly. Thirty seconds for a simple text extraction.",
        "And the fix was already installed on the system.",
        "Agent browser was there the whole time.",
        "But instead they went straight to raw CDP and Chrome flags.",
        "Classic mistake. Build from scratch when a tool exists.",
        "The hierarchy should be: existing script, existing tool, then build.",
        "And measure before you act. Not after six failed attempts.",
        "Eighty-eight percent of the time was pure waste.",
        "Waiting for a SPA to idle. For TensorFlow Lite to warm up.",
        "Next time, we check what's in the toolbox first.",
        "And we think before we type.",
    ],
    "code-review": [
        "Let's compare the two approaches side by side.",
        "On the left, the manual approach. Curl, then Chrome dump-dom, then CDP experiments.",
        "Each step took longer than expected. We kept trying lower-level solutions.",
        "On the right, the final script. Agent browser, three commands. Done in three point five seconds.",
        "Same result. Eight times faster. And the tool was installed all along.",
    ],
    "timeline": [
        "Here's the full timeline of what happened.",
        "Minute zero: we curl the URL. One second. Just an HTML shell.",
        "Minute one: we try grep patterns. Nothing useful found.",
        "Minute two: we start Chrome dump-dom. It will take thirty seconds.",
        "Minute thirty-two: dump-dom finishes. Full DOM at last.",
        "But then we waste more time on CDP experiments. All failed.",
        "Minute thirty-five: we try agent-browser.",
        "Three point five seconds. Done. Perfect.",
        "Thirty six minutes total. Most of it was going down the wrong path.",
    ],
}


def check_deps():
    for cmd in ["remotion", "edge-tts", "ffmpeg"]:
        result = subprocess.run(["which", cmd], capture_output=True)
        if result.returncode != 0:
            print(f"Missing dependency: {cmd}", file=sys.stderr)
            return False
    return True


def generate_tts(text_lines, filename):
    """Generate TTS audio for a list of text lines, returns list of audio file paths."""
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    audio_files = []
    
    for i, line in enumerate(text_lines):
        if not line.strip():
            continue
        out_path = TTS_DIR / f"{filename}_{i:03d}.mp3"
        if not out_path.exists():
            voice = "en-US-JennyNeural" if i % 2 == 0 else "en-US-GuyNeural"
            result = subprocess.run(
                ["edge-tts", "--voice", voice, "--text", line,
                 "--write-media", str(out_path)],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                print(f"TTS error for line {i}: {result.stderr[:100]}", file=sys.stderr)
                continue
        audio_files.append(str(out_path))
    
    return audio_files


def concat_audio(audio_files, output_path):
    """Concatenate MP3 files into one."""
    if len(audio_files) == 1:
        os.rename(audio_files[0], output_path)
        return str(output_path)
    
    list_path = TTS_DIR / "concat_list.txt"
    with open(list_path, "w") as f:
        for af in audio_files:
            f.write(f"file '{af}'\n")
    
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(list_path), "-c", "copy", str(output_path)],
        capture_output=True, check=True, timeout=30
    )
    list_path.unlink()
    return str(output_path)


def render_composition(comp_id, duration, audio_path=None):
    """Render a single composition with optional audio."""
    output = OUTPUT / f"{comp_id}.mp4"
    
    cmd = [
        "remotion", "render", str(SRC / "index.ts"), comp_id,
        str(output),
        "--overwrite",
    ]
    
    if audio_path:
        cmd.extend(["--audio", audio_path])
    
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    t = time.time() - t0
    
    if result.returncode != 0:
        print(f"Render error for {comp_id}: {result.stderr[:300]}", file=sys.stderr)
        return None
    
    return str(output), t


def main():
    start = time.time()
    
    if not check_deps():
        sys.exit(1)
    
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(COMPOSITIONS.keys())
    
    for comp_id in targets:
        if comp_id not in COMPOSITIONS:
            print(f"Unknown composition: {comp_id}. Available: {list(COMPOSITIONS.keys())}", file=sys.stderr)
            continue
        
        print(f"\n=== Generating '{comp_id}' ===")
        script = NARRATION_SCRIPTS.get(comp_id, [])
        
        # Generate TTS
        if script:
            print(f"  Generating {len(script)} TTS segments...")
            audio_files = generate_tts(script, comp_id)
            if audio_files:
                audio_concat = OUTPUT / f"{comp_id}_audio.mp3"
                audio_path = concat_audio(audio_files, audio_concat)
                print(f"  Audio: {audio_path}")
            else:
                audio_path = None
        else:
            audio_path = None
        
        # Render
        print(f"  Rendering video...")
        result = render_composition(comp_id, 0, audio_path)
        if result:
            path, t = result
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"  Done: {path}")
            print(f"  Time: {t:.1f}s, Size: {size_mb:.1f}MB")
    
    total = time.time() - start
    print(f"\n=== Total: {total:.1f}s ===")


if __name__ == "__main__":
    main()
