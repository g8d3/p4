#!/usr/bin/env python3
"""
Verify video quality against source files.

Checks timing, content, cadence, and font fit.

Usage:
    python verify_video_quality.py output/ch1.mp4 --source "original text" --ass output/ch1.ass --vtt output/ch1.vtt
"""

import sys, os, re, json, math

# Thresholds
MAX_CHUNK_DUR = 3.0      # seconds: a single chunk should not exceed this
MIN_CHUNK_DUR = 0.2      # seconds: a chunk should not be shorter than this
TARGET_WORDS_PER_SEC = 2.5  # average speaking rate in English
MAX_GAP_MS = 200         # max allowed gap between cues in milliseconds
MIN_OVERLAP_MS = -50     # negative = allowed underlap in ms (ffmpeg precision)
FONT_CHARS_AT_48 = 25    # chars that fit at font 48 on 608px width

RESULT = {"passed": 0, "failed": 0, "warnings": [], "errors": []}


def check(name, condition, detail=""):
    if condition:
        RESULT["passed"] += 1
    else:
        RESULT["failed"] += 1
        RESULT["errors"].append(f"FAIL: {name} — {detail}")


def warn(name, detail=""):
    RESULT["warnings"].append(f"WARN: {name} — {detail}")


def parse_ass(path):
    """Parse ASS file into dialogue events with start/end times and text."""
    events = []
    with open(path) as f:
        in_events = False
        for line in f:
            if line.startswith("[Events]"):
                in_events = True
                continue
            if in_events and line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    start_str = parts[1].strip()
                    end_str = parts[2].strip()
                    text = parts[9].strip()
                    def to_sec(s):
                        parts = s.split(":")
                        h = int(parts[0])
                        m = int(parts[1])
                        sec = float(parts[2].replace(",", "."))
                        return h*3600 + m*60 + sec
                    events.append({
                        "start": to_sec(start_str),
                        "end": to_sec(end_str),
                        "text": text,
                    })
    return events


def parse_vtt(path):
    """Parse VTT into cues."""
    with open(path) as f:
        content = f.read()
    cues = []
    lines = content.strip().split("\n")
    for i, line in enumerate(lines):
        if "-->" in line:
            parts = line.split(" --> ")
            def ts(s):
                s = s.replace(",", ".")
                parts = s.split(":")
                h = int(parts[0])
                m = int(parts[1])
                sec = float(parts[2])
                return h*3600 + m*60 + sec
            start = ts(parts[0].strip())
            end = ts(parts[1].strip())
            for j in range(i+1, len(lines)):
                if lines[j].strip() and "-->" not in lines[j]:
                    cues.append({"text": lines[j].strip(), "start": start, "end": end})
                    break
    return cues


def strip_ass_tags(text):
    """Remove ASS formatting tags like {\\c&H...&}."""
    return re.sub(r'\{[^}]*\}', '', text).strip()


def get_video_duration(path):
    """Get duration of video file using ffprobe."""
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=15)
    return float(r.stdout.strip()) if r.stdout.strip() else 0


# --- Verification functions ---

def verify_timing(ass_events, vtt_cues, video_dur):
    """Check timing integrity: gaps, overlaps, duration match."""
    
    # 1. Duration match
    if ass_events:
        ass_dur = ass_events[-1]["end"]
        diff = abs(ass_dur - video_dur)
        check(f"ASS end ({ass_dur:.2f}s) vs video ({video_dur:.2f}s)",
              diff < 0.5, f"diff={diff:.2f}s")
    
    # 2. Gaps and overlaps between consecutive ASS cues
    for i in range(1, len(ass_events)):
        gap_ms = (ass_events[i]["start"] - ass_events[i-1]["end"]) * 1000
        if gap_ms > MAX_GAP_MS:
            warn(f"Gap of {gap_ms:.0f}ms between cue {i-1} and {i}",
                 f"cue {i-1} ends at {ass_events[i-1]['end']:.2f}, cue {i} starts at {ass_events[i]['start']:.2f}")
        elif gap_ms < MIN_OVERLAP_MS:
            warn(f"Overlap of {-gap_ms:.0f}ms between cue {i-1} and {i}")
    
    # 3. No cue should be too long or too short
    for i, ev in enumerate(ass_events):
        dur = ev["end"] - ev["start"]
        if dur > MAX_CHUNK_DUR:
            warn(f"Cue {i} duration {dur:.2f}s exceeds {MAX_CHUNK_DUR}s",
                 f"text: {strip_ass_tags(ev['text'][:60])}")
        if dur < MIN_CHUNK_DUR:
            warn(f"Cue {i} duration {dur:.2f}s below {MIN_CHUNK_DUR}s")
    
    # 4. VTT phrases should be covered by at least one overlapping ASS cue
    for vc in vtt_cues:
        overlapping = [e for e in ass_events if e["start"] < vc["end"] and e["end"] > vc["start"]]
        if not overlapping:
            warn(f"VTT phrase '{vc['text'][:40]}' ({vc['start']:.1f}-{vc['end']:.1f}) has no overlapping ASS cue")


def verify_content(ass_events, source_text, vtt_cues):
    """Check that all source words appear in the subtitles."""
    
    # Normalize: lowercase, remove punctuation
    def normalize(t):
        return re.sub(r'[^\w\s]', '', t.lower()).split()
    
    source_words = set(normalize(source_text))
    ass_words = set()
    for ev in ass_events:
        clean = strip_ass_tags(ev["text"])
        ass_words.update(normalize(clean))
    
    vtt_words = set()
    for c in vtt_cues:
        vtt_words.update(normalize(c["text"]))
    
    # Words in source but missing from ASS
    missing_from_ass = source_words - ass_words
    if missing_from_ass:
        # Filter out very short words that might be split differently
        significant = {w for w in missing_from_ass if len(w) > 2}
        if significant:
            check("All source words appear in ASS subtitles",
                  False, f"missing: {', '.join(sorted(significant))}")
        else:
            warn(f"Only short words missing from ASS: {', '.join(sorted(missing_from_ass))}")
    else:
        RESULT["passed"] += 1
    
    # Words in VTT but not in source (VTT should be a subset)
    extra_in_vtt = vtt_words - source_words
    if extra_in_vtt:
        warn(f"VTT contains words not in source: {', '.join(sorted(extra_in_vtt))}")


def verify_cadence(ass_events, vtt_cues):
    """Check that highlighting cadence is natural.
    
    Count only NEWLY highlighted words per cue, not the full phrase text.
    Each ASS cue highlights a chunk while showing the full phrase.
    """
    if len(ass_events) < 2:
        check("At least 2 ASS cues", False, f"only got {len(ass_events)}")
        return
    
    total_dur = ass_events[-1]["end"] - ass_events[0]["start"]
    
    # Count words in VTT (the actual spoken words) instead of ASS (which repeats full phrases)
    total_words = sum(len(c["text"].split()) for c in vtt_cues)
    
    wps = total_words / total_dur if total_dur > 0 else 0
    
    check(f"Words per second ({wps:.1f}) within range [{TARGET_WORDS_PER_SEC-1}, {TARGET_WORDS_PER_SEC+1}]",
           abs(wps - TARGET_WORDS_PER_SEC) < 1.0,
           f"got {wps:.1f} wps, target {TARGET_WORDS_PER_SEC}")
    
    # Chunks per second (interruption rate)
    cps = len(ass_events) / total_dur
    check(f"ASS cue cadence ({cps:.2f} cues/s) in range [0.3, 2.0]",
           0.3 <= cps <= 2.0,
           f"got {cps:.2f} cps")


def verify_font_fit(ass_events, font_size=36, width=608):
    """Check if longest ASS line would overflow the frame."""
    max_chars = max(len(strip_ass_tags(e["text"])) for e in ass_events)
    # At font 48, ~25 chars fit in 608px. Scale by font size.
    est_chars = (font_size / 48) * FONT_CHARS_AT_48
    lines_needed = math.ceil(max_chars / est_chars)
    
    check(f"Longest line ({max_chars} chars) fits with wrapping at font {font_size}",
           lines_needed <= 6,
           f"would need {lines_needed} lines (ASS auto-wraps, 6 lines max recommended)")


def verify_visual_variety(ass_events, segments):
    """Check that visual variety is adequate."""
    types = set(seg["type"] for seg in segments)
    check(f"At least 2 visual types used: {types}",
           len(types) >= 2,
           f"only got types: {types}")
    
    # Check that segments aren't too short or too long
    for i, seg in enumerate(segments):
        if seg["duration"] > 12:
            warn(f"Segment {i} ({seg['type']}) duration {seg['duration']:.1f}s exceeds 12s")
        if seg["duration"] < 1.5 and i > 0:
            warn(f"Segment {i} ({seg['type']}) duration {seg['duration']:.1f}s is very short")


def verify_all(video_path, source_text, ass_path, vtt_path, segments=None, font_size=36):
    """Run all verification checks."""
    
    print(f"\n{'='*50}")
    print(f"Verification Report")
    print(f"{'='*50}")
    print(f"Video: {os.path.basename(video_path)}")
    print(f"ASS:   {os.path.basename(ass_path)}")
    print(f"VTT:   {os.path.basename(vtt_path)}")
    print(f"{'='*50}\n")
    
    # Parse all files
    ass_events = parse_ass(ass_path)
    vtt_cues = parse_vtt(vtt_path)
    video_dur = get_video_duration(video_path)
    
    print(f"ASS events: {len(ass_events)}")
    print(f"VTT cues:   {len(vtt_cues)}")
    print(f"Video:      {video_dur:.2f}s\n")
    
    if not ass_events:
        check("ASS file has events", False, "ASS file is empty or unparseable")
        return RESULT
    
    # Run checks
    verify_timing(ass_events, vtt_cues, video_dur)
    verify_content(ass_events, source_text, vtt_cues)
    verify_cadence(ass_events, vtt_cues)
    verify_font_fit(ass_events, font_size)
    
    if segments:
        verify_visual_variety(ass_events, segments)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Summary: {RESULT['passed']} passed, {RESULT['failed']} failed, "
          f"{len(RESULT['warnings'])} warnings")
    if RESULT['warnings']:
        print("\nWarnings:")
        for w in RESULT['warnings']:
            print(f"  {w}")
    if RESULT['errors']:
        print("\nErrors:")
        for e in RESULT['errors']:
            print(f"  {e}")
    print(f"{'='*50}\n")
    
    return RESULT


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Verify generated video")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--source", help="Original source text (or pass via stdin)")
    parser.add_argument("--ass", required=True, help="Path to ASS subtitle file")
    parser.add_argument("--vtt", required=True, help="Path to VTT subtitle file")
    parser.add_argument("--font-size", type=int, default=36, help="ASS font size used")
    args = parser.parse_args()
    
    source = args.source or sys.stdin.read().strip()
    
    verify_all(args.video, source, args.ass, args.vtt, font_size=args.font_size)
    
    if RESULT["failed"] > 0:
        sys.exit(1)
