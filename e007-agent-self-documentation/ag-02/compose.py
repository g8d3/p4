#!/usr/bin/env python3
"""Step 5: Compose final video from segments + narration."""

import os
import subprocess


def compose_video(segment_frames: list[dict], narration_path: str, output_path: str) -> bool:
    """Compose final video from segment frame videos + narration audio.

    segment_frames: [{"frame": path, "duration": float}, ...]
    """
    abs_output = os.path.abspath(output_path)
    abs_narration = os.path.abspath(narration_path)

    # Step 1: Concat video segments
    concat_list = os.path.join(os.path.dirname(abs_output), "concat.txt")
    with open(concat_list, "w") as f:
        for seg in segment_frames:
            f.write(f"file '{os.path.abspath(seg['frame'])}'\n")

    video_only = abs_output.replace(".mp4", "_video_only.mp4")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        video_only,
    ]
    r1 = subprocess.run(cmd_concat, capture_output=True, text=True, timeout=60)
    if r1.returncode != 0 or not os.path.exists(video_only):
        print(f"  Concat failed: {r1.stderr[-300:]}")
        return False

    # Step 2: Mux with narration audio
    cmd_mux = [
        "ffmpeg", "-y",
        "-i", video_only,
        "-i", abs_narration,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        abs_output,
    ]
    r2 = subprocess.run(cmd_mux, capture_output=True, text=True, timeout=60)

    # Cleanup
    if os.path.exists(video_only):
        os.remove(video_only)
    if os.path.exists(concat_list):
        os.remove(concat_list)

    return r2.returncode == 0 and os.path.exists(abs_output)
