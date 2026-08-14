#!/usr/bin/env python3
"""E02 subtitles: short TikTok-style chunks from Deepgram word timestamps."""
import json

WORDS = json.load(open("/home/vuos/code/p4/e023-build-in-public/ag-01/output/ep2_narration.words.json"))


def ts(t):
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


chunks = []
cur = []
for w in WORDS:
    if not cur:
        cur = [w]
        continue
    gap = w["start"] - cur[-1]["end"]
    dur = w["end"] - cur[0]["start"]
    if gap > 0.9 or len(cur) >= 6 or dur > 3.6:
        chunks.append(cur)
        cur = [w]
    else:
        cur.append(w)
if cur:
    chunks.append(cur)

lines = []
for i, c in enumerate(chunks, 1):
    text = " ".join(x["text"] for x in c)
    lines.append(f"{i}\n{ts(c[0]['start'])} --> {ts(c[-1]['end'])}\n{text}\n")

srt = "\n".join(lines)
with open("/home/vuos/code/p4/e023-build-in-public/ag-01/output/ep2_subs.srt", "w") as f:
    f.write(srt)
print(f"{len(chunks)} subtitle chunks, last end {ts(chunks[-1][-1]['end'])}")
print("\n".join(lines[:12]))
