"""Replay a .tds file: reconstruct as plain text timeline or feed to LLM."""

from __future__ import annotations

import argparse
import sys
from typing import Dict, List

from .stream import read_stream, StreamEvent, ChannelState


def reconstruct_timeline(path: str, compact: bool = False) -> List[str]:
    """Read a .tds file and produce a human-readable timeline."""
    events = read_stream(path)
    lines: List[str] = []
    channels: Dict[str, ChannelState] = {}

    for ev in events:
        if ev.kind == "KEYFRAME":
            lines.append(f"\n{'='*60}")
            lines.append(f"[t={ev.timestamp:.1f}] KEYFRAME (full state)")
            for op in ev.ops:
                lines.append(f"  {op}")

        elif ev.kind == "DELTA":
            if compact and len(ev.ops) > 5:
                lines.append(f"[t={ev.timestamp:.1f}] {ev.channel}: {len(ev.ops)} changes")
            else:
                lines.append(f"[t={ev.timestamp:.1f}] {ev.channel}:")
                for op in ev.ops[:20]:
                    lines.append(f"  {op}")
                if len(ev.ops) > 20:
                    lines.append(f"  ... ({len(ev.ops)} ops total)")

        elif ev.kind == "ADD":
            url = ev.meta.get("url", "")
            title = ev.meta.get("title", "")
            lines.append(f"[t={ev.timestamp:.1f}] ++ {ev.channel}: {title} ({url})")

        elif ev.kind == "REMOVE":
            lines.append(f"[t={ev.timestamp:.1f}] -- {ev.channel} closed")

    return lines


def main():
    parser = argparse.ArgumentParser(description="Replay a .tds stream")
    parser.add_argument("input", help=".tds file to replay")
    parser.add_argument("--compact", "-c", action="store_true",
                        help="Compact mode (group large deltas)")
    args = parser.parse_args()

    timeline = reconstruct_timeline(args.input, compact=args.compact)
    for line in timeline:
        print(line)


if __name__ == "__main__":
    main()
