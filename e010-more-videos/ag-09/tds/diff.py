"""Diff engine: compute structured deltas between two text snapshots."""

from __future__ import annotations

import difflib
from typing import List, Tuple


DiffOp = Tuple[str, str]  # ("+", "added line") or ("-", "removed line") or ("=", "same line")


def diff_snapshots(before: List[str], after: List[str]) -> List[DiffOp]:
    """Compare two snapshots (list of lines) and return minimal delta.

    Returns operations in order: removals (-) then additions (+).
    Uses difflib.SequenceMatcher for minimal diffs.
    """
    matcher = difflib.SequenceMatcher(None, before, after)
    ops: List[DiffOp] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "replace":
            for line in before[i1:i2]:
                ops.append(("~", line))
            for line in after[j1:j2]:
                ops.append(("+", line))
        elif tag == "delete":
            for line in before[i1:i2]:
                ops.append(("-", line))
        elif tag == "insert":
            for line in after[j1:j2]:
                ops.append(("+", line))
    return ops


def snapshot_key(lines: List[str]) -> str:
    """Hash a snapshot for quick equality check."""
    return "\n".join(lines)


def trim_to_visible(lines: List[str], max_lines: int = 200, max_cols: int = 200) -> List[str]:
    """Trim snapshot to sane limits: max lines, max columns per line.

    Prevents memory blowup from huge terminal scrollback or huge DOM.
    """
    trimmed = []
    for line in lines[-max_lines:]:
        if len(line) > max_cols:
            trimmed.append(line[:max_cols] + "...")
        else:
            trimmed.append(line)
    return trimmed
