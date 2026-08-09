#!/usr/bin/env python3
"""Recover original KIE WAV URLs for all 11 TTS chunks from the task log."""
import re, json, subprocess, sys, time

LOG = "/home/vuos/code/p4/e023-build-in-public/ag-01/output/logs.txt"
KEY = __import__("os").environ.get("KIE_API_KEY", "")

# Parse tasks: (timestamp, task_id, text, credits)
tasks = []
for b in re.split(r"^\s*-\s*$", open(LOG).read(), flags=re.M):
    m_text = re.search(r'"text":"(.*?)"', b, re.S)
    m_id = re.search(r"^([0-9a-f]{32})\s*$", b, re.M)
    m_time = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", b)
    m_cred = re.search(r"^([\d.]+)\s*$", b, re.M)
    if m_text and m_id:
        tasks.append({
            "time": m_time.group(1) if m_time else "?",
            "id": m_id.group(1),
            "text": m_text.group(1),
            "credits": m_cred.group(1) if m_cred else "?",
        })

def match_chunk(task):
    """Return chunk id this task belongs to, or None."""
    t = task["text"][:60]
    table = {
        "If you backtest a trading bot": "00",
        "Sounds clever. Let's see": "01",
        "A two point seven profit factor": "02",
        "The clean plus fifty percent edge": "03",
        "Then I validated both out of sample": "04",
        "That is the overfit, caught on camera": "05",
        "The strategy isn't losing because": "06",
        "Rebalancing anchors long": "07",
        "Now let me be completely honest": "08",
        "Here's the honest truth": "09",
        "If you found this useful": "10",
    }
    for k, c in table.items():
        if t.startswith(k):
            return c
    return None

for task in tasks:
    task["chunk"] = match_chunk(task)

# For duplicated chunks, pick the task closest to the mp3 file's saved timestamp
# chunk -> preferred mp3 save time (from local filenames)
mp3_time = {  # chunk: HH:MM:SS of the *_cXX*.mp3 (the one actually used)
    "00": "00:08:30", "01": "00:08:46", "02": "00:09:01", "03": "00:10:05",
    "04": "00:16:53", "05": "00:10:32", "06": "00:10:51", "07": "00:11:45",
    "08": "00:12:27", "09": "00:12:42", "10": "00:13:20",
}
def to_sec(hms):
    h, m, s = hms.split(":")
    return int(h)*3600 + int(m)*60 + int(s)

# group by chunk
from collections import defaultdict
by_chunk = defaultdict(list)
for t in tasks:
    if t["chunk"]:
        by_chunk[t["chunk"]].append(t)

chosen = {}
for c, group in sorted(by_chunk.items()):
    if len(group) == 1:
        chosen[c] = group[0]
    else:
        target = to_sec(mp3_time[c])
        chosen[c] = min(group, key=lambda t: abs(to_sec(t["time"][11:]) - target))

print("=== Task IDs por chunk (los elegidos) ===")
for c in sorted(chosen):
    t = chosen[c]
    print(f"chunk {c}: {t['id']}  ({t['time']}, {t['credits']} cr)")

# Now query recordInfo for each and print result URLs
print("\n=== Consultando recordInfo ===")
urls = {}
for c in sorted(chosen):
    tid = chosen[c]["id"]
    r = subprocess.run(
        ["curl", "-sS", f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={tid}",
         "-H", f"Authorization: Bearer {KEY}"],
        capture_output=True, text=True, timeout=30)
    try:
        d = json.loads(r.stdout)
        data = d.get("data", {})
        rj = data.get("resultJson", "{}")
        if isinstance(rj, str):
            rj = json.loads(rj)
        urls[c] = rj.get("resultUrls", [])
        print(f"chunk {c}: state={data.get('state')} urls={urls[c]}")
    except Exception as e:
        print(f"chunk {c}: ERROR {e} :: {r.stdout[:200]}")
    time.sleep(0.3)

with open("/tmp/opencode/kie_urls.json", "w") as f:
    json.dump(urls, f, indent=2)
print("\n>>> URLs guardadas en /tmp/opencode/kie_urls.json")
