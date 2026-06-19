#!/usr/bin/env python3
"""Step 2: Score and select segments for video."""

from dataclasses import dataclass, field
from parse import Session, Part


@dataclass
class Segment:
    index: int
    start_time: int
    end_time: int
    parts: list[Part] = field(default_factory=list)
    score: float = 0.0
    label: str = ""  # hook, exploration, analysis, conclusion
    display_text: str = ""
    narration_hint: str = ""


def score_part(part: Part) -> float:
    """Score a single part for watchability."""
    if part.type == "text":
        text = part.text.lower()
        if any(kw in text for kw in ["?", "cómo", "que es", "explain", "cuál", "cuáles"]):
            return 10.0  # user question
        if any(kw in text for kw in ["conclusión", "resumen", "takeaway", "la diferencia"]):
            return 9.0  # conclusion/insight
        if len(part.text) > 50:
            return 7.0  # substantial agent response
        return 5.0  # short text

    elif part.type == "tool":
        tool = part.tool_name.lower()
        if tool in ("bash", "shell"):
            return 8.0  # command execution = action
        if tool == "read":
            return 4.0  # reading files = low interest
        if tool in ("write", "edit"):
            return 7.0  # writing code = interesting
        return 5.0

    elif part.type == "reasoning":
        return 2.0  # thinking = show as indicator only

    elif part.type == "patch":
        return 6.0  # code changes = moderately interesting

    elif part.type in ("step-start", "step-finish"):
        return 0.5  # navigation markers

    return 1.0


def group_into_segments(parts: list[Part], max_duration: int = 90) -> list[Segment]:
    """Group parts into narrative segments, targeting max_duration seconds."""
    if not parts:
        return []

    segments = []
    current_segment_parts = []
    current_score = 0.0
    seg_index = 0

    # Calculate total session duration
    total_duration = (parts[-1].time_created - parts[0].time_created) / 1000
    target_per_segment = min(20, total_duration / 4)  # ~4 segments

    for part in parts:
        current_segment_parts.append(part)
        current_score += score_part(part)

        # Check if we should end this segment
        elapsed = (part.time_created - (current_segment_parts[0].time_created)) / 1000
        if elapsed >= target_per_segment and len(current_segment_parts) >= 2:
            # Find the best display text from this segment
            best_part = max(current_segment_parts, key=lambda p: score_part(p))
            display = _get_display_text(best_part)

            avg_score = current_score / len(current_segment_parts)
            segments.append(Segment(
                index=seg_index,
                start_time=current_segment_parts[0].time_created,
                end_time=current_segment_parts[-1].time_created,
                parts=current_segment_parts[:],
                score=avg_score,
                display_text=display,
            ))
            seg_index += 1
            current_segment_parts = []
            current_score = 0.0

    # Remaining parts
    if current_segment_parts:
        best_part = max(current_segment_parts, key=lambda p: score_part(p))
        display = _get_display_text(best_part)
        avg_score = current_score / len(current_segment_parts)
        segments.append(Segment(
            index=seg_index,
            start_time=current_segment_parts[0].time_created,
            end_time=current_segment_parts[-1].time_created,
            parts=current_segment_parts[:],
            score=avg_score,
            display_text=display,
        ))

    # Label segments by position
    if segments:
        segments[0].label = "hook"
        if len(segments) > 1:
            for s in segments[1:-1]:
                s.label = "exploration"
            segments[-1].label = "conclusion"

    return segments


def select_top_segments(segments: list[Segment], target_count: int = 5) -> list[Segment]:
    """Select the most interesting segments, keeping narrative order."""
    if len(segments) <= target_count:
        return segments

    # Always keep hook and conclusion
    hook = [s for s in segments if s.label == "hook"]
    conclusion = [s for s in segments if s.label == "conclusion"]
    middle = [s for s in segments if s.label not in ("hook", "conclusion")]

    # Score middle segments and pick top N
    available = target_count - len(hook) - len(conclusion)
    if available > 0 and middle:
        middle_sorted = sorted(middle, key=lambda s: s.score, reverse=True)
        selected_middle = sorted(middle_sorted[:available], key=lambda s: s.start_time)
    else:
        selected_middle = []

    return hook + selected_middle + conclusion


def _get_display_text(part: Part) -> str:
    """Extract the best display text from a part."""
    if part.type == "text":
        return part.text[:120]
    if part.type == "tool":
        return f"$ {part.tool_name}({part.tool_input[:60]})"
    if part.type == "patch":
        return f"edit: {part.file_path}"
    if part.type == "reasoning":
        return f"thinking... ({len(part.text)} chars)"
    return part.type


def generate_narration_script(segments: list[Segment], session_title: str) -> str:
    """Generate a Spanish narration script for the video."""
    lines = [f"# {session_title}", ""]
    for seg in segments:
        lines.append(f"## [{seg.label.upper()}] Segment {seg.index}")
        lines.append(f"Duration: ~10s")
        lines.append(f"Parts: {len(seg.parts)} ({', '.join(set(p.type for p in seg.parts))})")
        lines.append(f"Display: {seg.display_text[:80]}")
        lines.append("")
    return "\n".join(lines)
