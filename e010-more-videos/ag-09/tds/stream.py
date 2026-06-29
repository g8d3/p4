"""TDS stream format: reader and writer for .tds files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class ChannelState:
    """Represents the full state of one channel at a point in time."""
    channel_id: str
    channel_type: str  # "terminal" | "browser"
    lines: List[str] = field(default_factory=list)
    meta: Dict[str, str] = field(default_factory=dict)


@dataclass
class StreamEvent:
    """One event in the TDS stream."""
    kind: str            # "KEYFRAME" | "DELTA" | "ADD" | "REMOVE"
    timestamp: float     # seconds from start
    channel: str         # e.g. "term(1)", "browser(1)"
    ops: List[str] = field(default_factory=list)   # formatted diff lines
    meta: Dict[str, str] = field(default_factory=dict)


def format_event(ev: StreamEvent) -> str:
    """Format a StreamEvent as a .tds line block."""
    lines = []
    if ev.kind == "KEYFRAME":
        lines.append(f"KEYFRAME t={ev.timestamp:.1f}")
    elif ev.kind == "DELTA":
        lines.append(f"DELTA t={ev.timestamp:.1f} ch={ev.channel}")
    elif ev.kind == "ADD":
        lines.append(f"ADD ch={ev.channel} t={ev.timestamp:.1f}")
        for k, v in ev.meta.items():
            lines.append(f"  {k}={v!r}")
    elif ev.kind == "REMOVE":
        lines.append(f"REMOVE ch={ev.channel} t={ev.timestamp:.1f}")

    if ev.kind in ("KEYFRAME", "DELTA"):
        for k, v in ev.meta.items():
            lines.append(f"  {k}={v!r}")
        lines.append(f"  content:")
        for line in ev.ops:
            if ev.kind == "DELTA":
                lines.append(f"  {_format_op(line)}")
            else:
                lines.append(f"  {line}")

    lines.append("")
    return "\n".join(lines)


def _format_op(op: str) -> str:
    """Convert an op string like '+ hello' to pipe-delimited '+| hello'.

    The pipe makes leading whitespace in content unambiguous.
    """
    if len(op) >= 2 and op[0] in "+-~" and op[1] == " ":
        return op[0] + "|" + op[2:]
    return op


def _parse_op(line: str) -> str:
    """Convert a pipe-delimited op back: '+| hello' -> '+ hello'."""
    if len(line) >= 2 and line[0] in "+-~" and line[1] == "|":
        return line[0] + " " + line[2:]
    return line


def parse_event(block: str) -> Optional[StreamEvent]:
    """Parse a .tds event block back into a StreamEvent."""
    lines = block.rstrip("\n").split("\n")
    if not lines:
        return None

    header = lines[0]

    m = re.match(r"KEYFRAME t=([\d.]+)", header)
    if m:
        ev = StreamEvent(kind="KEYFRAME", timestamp=float(m.group(1)), channel="*")
        _parse_body(lines[1:], ev)
        return ev

    m = re.match(r"DELTA t=([\d.]+) ch=(\S+)", header)
    if m:
        ev = StreamEvent(kind="DELTA", timestamp=float(m.group(1)), channel=m.group(2))
        _parse_body(lines[1:], ev)
        return ev

    m = re.match(r"ADD ch=(\S+) t=([\d.]+)", header)
    if m:
        ev = StreamEvent(kind="ADD", timestamp=float(m.group(2)), channel=m.group(1))
        _parse_meta(lines[1:], ev)
        return ev

    m = re.match(r"REMOVE ch=(\S+) t=([\d.]+)", header)
    if m:
        return StreamEvent(kind="REMOVE", timestamp=float(m.group(2)), channel=m.group(1))

    return None


def _parse_body(lines: List[str], ev: StreamEvent) -> None:
    in_content = False
    for line in lines:
        line = line.rstrip("\n")
        if line.startswith("  content:"):
            in_content = True
        elif in_content:
            # Lines are indented by 2 spaces under content:
            if line.startswith("  "):
                content = line[2:]
                if ev.kind == "DELTA":
                    content = _parse_op(content)
                ev.ops.append(content)
            else:
                ev.ops.append(line)
        elif "=" in line and not line.strip().startswith("-"):
            _parse_meta_line(line, ev)


def _parse_meta(lines: List[str], ev: StreamEvent) -> None:
    for line in lines:
        _parse_meta_line(line, ev)


def _parse_meta_line(line: str, ev: StreamEvent) -> None:
    m = re.match(r"\s+(\w+)=(?:\"([^\"]*)\"|'([^']*)')", line)
    if m:
        ev.meta[m.group(1)] = m.group(2) or m.group(3) or ""


def write_stream(events: List[StreamEvent], path: str) -> None:
    """Write a list of events to a .tds file."""
    with open(path, "w") as f:
        f.write("# TDS v1 - Text Delta Stream\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"# Events: {len(events)}\n")
        f.write("\n")
        for i, ev in enumerate(events):
            f.write(format_event(ev))
            if i < len(events) - 1:
                f.write("\n")  # blank line between events


def read_stream(path: str) -> List[StreamEvent]:
    """Read a .tds file back into events."""
    events = []
    current_block: List[str] = []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or line.strip() == "":
                if current_block:
                    ev = parse_event("".join(current_block))
                    if ev:
                        events.append(ev)
                    current_block = []
                continue
            current_block.append(line)
        if current_block:
            ev = parse_event("".join(current_block))
            if ev:
                events.append(ev)
    return events
