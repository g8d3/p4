import json

with open("../ag-03/timing.json") as f:
    timing = json.load(f)

cum = 0.0
entries = []
for seg in timing:
    start = cum
    end = cum + seg["duration"]
    # Format SRT timestamp: HH:MM:SS,mmm
    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    entries.append((fmt(start), fmt(end), seg["text"]))
    cum = end

with open("subtitles.srt", "w") as f:
    for i, (start, end, text) in enumerate(entries, 1):
        f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

print(f"Generated {len(entries)} SRT entries")
