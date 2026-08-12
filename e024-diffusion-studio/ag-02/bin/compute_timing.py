#!/usr/bin/env python3
"""Compute slide timings from measured part durations + paragraph word counts.

Narration was TTS'd in 3 parts (KIE truncation limit). Each part's mp3 duration
is measured exactly; within a part, slides are allocated proportionally to
paragraph word counts (uniform TTS pacing).
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(ROOT, "..", "output"))

# measured mp3 durations (ffprobe) for part1/2/3 in order
PART_DUR = [70.536, 76.368, 58.368]

PARTS = []
for i in range(1, 4):
    with open(f"/tmp/ag02-part{i}.txt") as f:
        paras = [p.strip() for p in f.read().strip().split("\n\n") if p.strip()]
    PARTS.append(paras)

slides = []
idx = 1
for part_paras, dur in zip(PARTS, PART_DUR):
    words = [len(p.split()) for p in part_paras]
    total = sum(words)
    starts = []
    t = 0.0
    for w in words:
        starts.append(t)
        t += dur * w / total
    for para, s in zip(part_paras, starts):
        slides.append({"index": idx, "paragraph": para, "start": round(s, 3),
                       "words": len(para.split()), "part_dur": round(dur, 3)})
        idx += 1

# clamp end of last slide to total duration
total_dur = sum(PART_DUR)
for i, sl in enumerate(slides):
    sl["end"] = round(slides[i + 1]["start"] if i + 1 < len(slides) else total_dur, 3)

timing = {"total_duration": round(total_dur, 3), "slides": slides}
with open(os.path.join(OUT, "timing.json"), "w") as f:
    json.dump(timing, f, indent=2)
print(f"total narration: {total_dur:.3f}s, {len(slides)} slides")
for sl in slides:
    print(f"  slide {sl['index']:02d}: {sl['start']:7.2f} - {sl['end']:7.2f}  ({sl['words']:3d}w)  {sl['paragraph'][:50]}...")
