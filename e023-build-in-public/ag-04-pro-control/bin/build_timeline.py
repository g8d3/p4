#!/usr/bin/env python3
"""E03 (Pro control) timeline: map slides to narration time ranges.
Chunk durations are measured from the actual TTS mp3s (via ffprobe)."""
import subprocess, os

OUT = "/home/vuos/code/p4/e023-build-in-public/ag-04-pro-control/output"
TTS = f"{OUT}/tts"

# chunk durations measured live (from tts_paths.txt + ffprobe fallback)
def dur(i):
    import re
    lines = open(f"{TTS}/tts_paths.txt").read().splitlines()
    path = lines[i].split(" ", 1)[1]
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())

D = [dur(i) for i in range(12)]
cum = []
t = 0.0
for d in D:
    cum.append(t)
    t += d
total = t
print("chunk durations:", [round(d, 2) for d in D])
print("total:", round(total, 2))

# slide -> (chunk, start_frac, end_frac)
SLIDES = [
    ("d00_title",    0, 0.00, 0.45),
    ("d01_question", 0, 0.45, 1.00),
    ("d02_setup",    1, 0.00, 0.55),
    ("d03_candle",   1, 0.55, 1.00),
    ("d05_fattails", 2, 0.00, 0.40),
    ("d06_fattail_mean", 2, 0.40, 0.75),
    ("ch_hist",      2, 0.75, 1.00),
    ("d07_volcluster", 3, 0.00, 0.60),
    ("d08_volinput", 3, 0.60, 1.00),
    ("d09_nulls",    4, 0.00, 1.00),
    ("d10_eventstudy", 5, 0.00, 0.45),
    ("d11_eventresult", 5, 0.45, 1.00),
    ("d12_oos",      6, 0.00, 0.60),
    ("d13_overfit",  6, 0.60, 1.00),
    ("d14_fees",     7, 0.00, 0.45),
    ("d15_ledger",   7, 0.45, 1.00),
    ("d16_small",    8, 0.00, 0.18),
    ("d17_t2",       8, 0.18, 0.36),
    ("d18_overlap",  8, 0.36, 0.54),
    ("d19_combined", 8, 0.54, 0.74),
    ("d20_baseline", 8, 0.74, 0.90),
    ("ch_equity",    8, 0.90, 1.00),
    ("d21_honest",   9, 0.00, 1.00),
    ("d22_monitor", 10, 0.00, 0.55),
    ("mon_capture", 10, 0.55, 1.00),
    ("d23_verdict", 11, 0.00, 0.70),
    ("d24_thanks",  11, 0.70, 1.00),
]

lines = []
for slide, p, s, e in SLIDES:
    start = cum[p] + D[p] * s
    end = cum[p] + D[p] * e
    lines.append((slide, start, end))

with open(f"{OUT}/timeline.txt", "w") as f:
    for slide, s, e in lines:
        f.write(f"{slide} {s:.2f} {e:.2f}\n")
for slide, s, e in lines:
    print(f"{slide:16} {s:7.2f} - {e:7.2f}")
print(f"total: {lines[-1][2]:.2f}s")
