#!/usr/bin/env python3
"""E02 timeline: map slides to narration time ranges (from chunk durations)."""
import json

# paragraph -> [start, end] from chunk durations (cumulative)
P = {
    0: [0.0, 34.608],
    1: [34.608, 65.472],
    2: [65.472, 111.168],
    3: [111.168, 151.632],
    4: [151.632, 202.248],
    5: [202.248, 242.256],
    6: [242.256, 279.312],
    7: [279.312, 331.728],
    8: [331.728, 395.352],
    9: [395.352, 427.536],
    10: [427.536, 482.904],
    11: [482.904, 521.448],
}

# slide -> (paragraph, start_frac, end_frac)
SLIDES = [
    ("d00_title", 0, 0.00, 0.35),
    ("d01_question", 0, 0.35, 1.00),
    ("d02_setup", 1, 0.00, 0.60),
    ("d03_candle", 1, 0.60, 1.00),
    ("d05_fattails", 2, 0.00, 0.35),
    ("d06_fattail_mean", 2, 0.35, 0.70),
    ("ch_hist", 2, 0.70, 1.00),
    ("d07_volcluster", 3, 0.00, 0.60),
    ("d08_volinput", 3, 0.60, 1.00),
    ("d09_nulls", 4, 0.00, 1.00),
    ("d10_eventstudy", 5, 0.00, 0.35),
    ("d11_eventresult", 5, 0.35, 0.70),
    ("ch_paths", 5, 0.70, 1.00),
    ("d12_oos", 6, 0.00, 0.60),
    ("d13_overfit", 6, 0.60, 1.00),
    ("d14_fees", 7, 0.00, 0.40),
    ("d15_ledger", 7, 0.40, 1.00),
    ("d16_small", 8, 0.00, 0.20),
    ("d17_t2", 8, 0.20, 0.40),
    ("d18_overlap", 8, 0.40, 0.60),
    ("d19_combined", 8, 0.60, 0.75),
    ("d20_baseline", 8, 0.75, 0.90),
    ("ch_equity", 8, 0.90, 1.00),
    ("d21_honest", 9, 0.00, 1.00),
    ("d22_monitor", 10, 0.00, 0.55),
    ("mon_capture_crop", 10, 0.55, 1.00),
    ("d23_verdict", 11, 0.00, 0.70),
    ("d24_thanks", 11, 0.70, 1.00),
]

lines = []
for slide, p, s, e in SLIDES:
    start = P[p][0] + (P[p][1] - P[p][0]) * s
    end = P[p][0] + (P[p][1] - P[p][0]) * e
    lines.append((slide, start, end))

with open("/home/vuos/code/p4/e023-build-in-public/ag-01/output/ep2_timeline.txt", "w") as f:
    for slide, s, e in lines:
        f.write(f"{slide} {s:.2f} {e:.2f}\n")
print("\n".join(f"{s} {a:.2f} {b:.2f}" for s, a, b in lines))
print(f"\ntotal: {lines[-1][2]:.2f}s")
