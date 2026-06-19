#!/usr/bin/env python3
"""Step 4: Generate Spanish narration with edge-tts (MP3)."""

import subprocess
import os
from score import Segment

VOICE = "es-CO-SalomeNeural"


def generate_segment_narration(segment: Segment, session_title: str, output_path: str) -> bool:
    """Generate narration text for a segment and produce MP3 audio."""
    text = _build_narration_text(segment, session_title)
    if not text:
        return False

    cmd = [
        "edge-tts",
        "--voice", VOICE,
        "--text", text,
        "--write-media", output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0 and os.path.exists(output_path)


def get_audio_duration(path: str) -> float:
    """Get duration of audio file in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 10.0


def _build_narration_text(segment: Segment, session_title: str) -> str:
    """Build Spanish narration text for a segment."""
    label = segment.label
    parts = segment.parts

    if label == "hook":
        user_parts = [p for p in parts if p.type == "text"]
        if user_parts:
            question = user_parts[0].text[:100]
            return f"Hoy vemos la sesión {session_title}. El usuario pregunta: {question}"
        return f"Hoy vemos la sesión {session_title}."

    elif label == "conclusion":
        text_parts = [p for p in parts if p.type == "text"]
        if text_parts:
            summary = text_parts[-1].text[:150]
            return f"La conclusión de la sesión: {summary}"
        return "La conclusión de la sesión."

    else:  # exploration, analysis
        tool_parts = [p for p in parts if p.type == "tool"]
        text_parts = [p for p in parts if p.type == "text"]

        narration_parts = []
        if text_parts:
            narration_parts.append(f"El agente dice: {text_parts[0].text[:80]}")
        if tool_parts:
            tool = tool_parts[0]
            narration_parts.append(f"Ejecuta {tool.tool_name}")

        if narration_parts:
            return ". ".join(narration_parts) + "."
        return f"Continúa la exploración de la sesión."


def combine_audio_files(audio_files: list[str], output_path: str) -> bool:
    """Combine multiple MP3 files into one using ffmpeg concat."""
    if not audio_files:
        return False

    concat_list = output_path.replace(".mp3", "_list.txt")
    with open(concat_list, "w") as f:
        for af in audio_files:
            f.write(f"file '{os.path.abspath(af)}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if os.path.exists(concat_list):
        os.remove(concat_list)
    return result.returncode == 0 and os.path.exists(output_path)
