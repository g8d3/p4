#!/usr/bin/env python3
import json
import re
import subprocess
import sys
import os

SCRIPT = "../ag-02/script.md"
VOICES = {"A": "es-CO-GonzaloNeural", "B": "es-CO-SalomeNeural"}

lines = []
with open(SCRIPT) as f:
    for line in f:
        m = re.match(r"^(A|B):\s*(.+)", line.strip())
        if m:
            lines.append((m.group(1), m.group(2).strip()))

print(f"Found {len(lines)} dialogue lines")

segments = []
for i, (speaker, text) in enumerate(lines, start=1):
    fname = f"seg_{i:03d}.mp3"
    voice = VOICES[speaker]
    print(f"[{i:03d}] {speaker} ({voice}): {text[:60]}...")
    result = subprocess.run(
        ["edge-tts", "--voice", voice, "--text", text, "--write-media", fname],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr}")
        sys.exit(1)
    # get duration via ffprobe
    dur_result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", fname],
        capture_output=True, text=True, timeout=30
    )
    duration = float(dur_result.stdout.strip() or 0)
    segments.append({
        "segment": i,
        "file": fname,
        "speaker": speaker,
        "voice": voice,
        "text": text,
        "duration": round(duration, 3)
    })
    print(f"  -> {fname} ({duration:.2f}s)")

with open("timing.json", "w") as f:
    json.dump(segments, f, indent=2, ensure_ascii=False)

print(f"\nDone. {len(segments)} segments generated.")
print("timing.json written.")
