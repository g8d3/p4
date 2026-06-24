#!/usr/bin/env python3
"""
make_subtitles.py — Generate TikTok-style SRT subtitles from narration text + audio duration.

Usage: python3 make_subtitles.py <audio.mp3> <text.txt> <output.srt>

Subtitles are short 2-4 word chunks, alternating colors (via ASS style).
"""

import sys
import os
import json
import subprocess
import re


def get_audio_duration(audio_path):
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 30.0  # fallback


def split_text_to_chunks(text, max_words=4):
    """Split text into short chunks of max_words words each."""
    # Split into sentences first
    sentences = re.split(r'[.!?]\s+', text.strip())
    chunks = []
    for sentence in sentences:
        words = sentence.split()
        if not words:
            continue
        # Split into chunks of max_words
        for i in range(0, len(words), max_words):
            chunk = ' '.join(words[i:i + max_words])
            if chunk.strip():
                chunks.append(chunk.strip())
    return chunks


def format_srt_time(seconds):
    """Format seconds to SRT timestamp HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    if len(sys.argv) < 4:
        print("Usage: make_subtitles.py <audio.mp3> <text.txt> <output.srt>")
        sys.exit(1)

    audio_path = sys.argv[1]
    text_path = sys.argv[2]
    output_path = sys.argv[3]

    # Read narration text
    with open(text_path) as f:
        text = f.read().strip()

    # Get audio duration
    duration = get_audio_duration(audio_path)

    # Split into chunks
    chunks = split_text_to_chunks(text, max_words=4)

    if not chunks:
        print("No text to subtitle")
        sys.exit(0)

    # Distribute time evenly across chunks, with small gaps
    total_chars = sum(len(c) for c in chunks)
    gap = 0.1  # seconds between subtitles
    usable_time = duration - (gap * len(chunks))
    if usable_time <= 0:
        usable_time = duration

    # Write SRT
    with open(output_path, 'w') as f:
        current_time = 0.0
        for i, chunk in enumerate(chunks):
            char_ratio = len(chunk) / max(total_chars, 1)
            chunk_duration = max(0.5, usable_time * char_ratio)

            start = format_srt_time(current_time)
            end = format_srt_time(min(current_time + chunk_duration, duration))

            f.write(f"{i + 1}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{chunk}\n\n")

            current_time += chunk_duration + gap

    print(f"Subtitles: {output_path} ({len(chunks)} chunks, {duration:.1f}s)")


if __name__ == "__main__":
    main()
