#!/usr/bin/env python3
"""Print Coco inbox entries newer than coco/.coco_last_read, then advance the marker.

Usage: coco_unread.py [--peek]  (--peek prints without moving the marker)
"""
import json
import os
import sys

COCO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "coco")
INBOX = os.path.join(COCO, "inbox_to_coco.jsonl")
MARKER = os.path.join(COCO, ".coco_last_read")


def load_entries():
    if not os.path.exists(INBOX):
        return []
    rows = []
    with open(INBOX, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main(argv):
    peek = "--peek" in argv
    last = ""
    if os.path.exists(MARKER):
        last = open(MARKER, encoding="utf-8").read().strip()
    rows = load_entries()
    fresh = []
    seen_marker = not last
    for r in rows:
        if seen_marker:
            fresh.append(r)
        elif r.get("id") == last:
            seen_marker = True
    for r in fresh:
        print(f"[{r.get('ts')}] {r.get('from')}: {r.get('msg')} (id={r.get('id')})")
    if fresh and not peek:
        with open(MARKER, "w", encoding="utf-8") as f:
            f.write(str(fresh[-1].get("id", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
