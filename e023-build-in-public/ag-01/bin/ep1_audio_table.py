#!/usr/bin/env python3
"""E01 audio-cut table: chunk timeline + text + active slide per window."""
import re, os

OUT = "/home/vuos/code/p4/e023-build-in-public/ag-01/output"

# TTS chunk boundaries (seconds)
CHUNKS = [
    (0, 28.944, "00"),
    (28.944, 62.016, "01"),
    (62.016, 90.48, "02"),
    (90.48, 121.632, "03"),
    (121.632, 150.648, "04"),
    (150.648, 184.992, "05"),
    (184.992, 218.112, "06"),
    (218.112, 249.84, "07"),
    (249.84, 275.52, "08"),
    (275.52, 301.416, "09"),
    (301.416, 306.528, "10"),
]

# slide timeline: (slide_idx, start, end)
SLIDES = [
    (0, 0, 5), (1, 5, 18), (2, 18, 33), (3, 33, 44), (4, 44, 57),
    (5, 57, 63), (6, 63, 77), (7, 77, 90), (8, 90, 99), (9, 99, 111),
    (10, 111, 122), (11, 122, 131), (12, 131, 139), (13, 139, 147),
    (14, 147, 155), (15, 155, 168), (16, 168, 181), (17, 181, 198),
    (18, 198, 219), (19, 219, 243), (20, 243, 252), (21, 252, 270),
    (22, 270, 306),
]
SLIDE_LABELS = {
    0: "+50% title", 1: "GRID strategy", 2: "20,000 bars", 3: "+20.9% range",
    4: "TUTORIALS STOP", 5: "RANGE +21%", 6: "-16% mixed", 7: "486 configs",
    8: "+54.8% reb48", 9: "+50% reb96", 10: "-1.9% OOS", 11: "-50.5% seed",
    12: "+23.8% held", 13: "105,122 bars", 14: "-20.6% v1", 15: "13,424 fills",
    16: "v2 redesign", 17: "+3.6% v2", 18: "+1.7% 1h", 19: "PF 1.14",
    20: "+8.4→-5.6 ridge", 21: "BACKTESTS LIE", 22: "thanks",
}

def ts(x):
    h=int(x//3600); m=int((x%3600)//60); s=x%60
    return f"{h:02d}:{m:02d}:{int(s):02d}"

def slide_at(t):
    for s,a,b in SLIDES:
        if a <= t < b:
            return s, SLIDE_LABELS[s]
    return None, ""

# chunk text
chunk_txt = {}
for i, c in enumerate(["00","01","02","03","04","05","06","07","08","09","10"]):
    p = f"{OUT}/tts/chunk_{c}.txt"
    if os.path.exists(p):
        chunk_txt[c] = open(p).read().strip().replace("\n", " ")

lines = []
lines.append("="*100)
lines.append("E01 — TABLA DE CORTES DE AUDIO (11 chunks TTS) + diapositiva activa")
lines.append("="*100)
lines.append("")
for a, b, c in CHUNKS:
    lines.append(f"\n### CHUNK {c}  [{ts(a)} → {ts(b)}]  ({b-a:.0f}s)")
    lines.append("-"*100)
    # what slide(s) are active during this chunk
    slides_in = []
    for s, x, y in SLIDES:
        if x < b and y > a:
            slides_in.append(f"slide {s} ({SLIDE_LABELS[s]}) {ts(max(a,x))}-{ts(min(b,y))}")
    lines.append(f"Diapositivas activas: {' | '.join(slides_in)}")
    # sub-chunks every ~10s with active slide at midpoint
    t = a
    while t < b:
        st = min(t+10, b)
        mid = (t+st)/2
        s, lab = slide_at(mid)
        lines.append(f"  [{ts(t)}-{ts(st)}] slide {s}: {lab}")
        t = st
    # chunk text
    lines.append(f"\n  TEXTO del chunk: \"{chunk_txt.get(c, '???')}\"")
    lines.append("")

report = "\n".join(lines)
print(report)
with open(f"{OUT}/audio-cut-table.md", "w") as f:
    f.write(report + "\n")
print(f"\n>>> guardado en {OUT}/audio-cut-table.md")
