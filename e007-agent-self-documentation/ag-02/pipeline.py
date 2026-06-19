#!/usr/bin/env python3
"""
ag-02: Interaction-to-Video pipeline.

Usage:
  python3 pipeline.py <session_id> [-o output_dir] [--render terminal|simple|both]
  python3 pipeline.py --list [directory]
"""

import argparse
import os
import sys
import time

from parse import get_session, list_sessions, export_session_json
from score import group_into_segments, select_top_segments, generate_narration_script
from narrate import generate_segment_narration, get_audio_duration, combine_audio_files
from compose import compose_video


def run_pipeline(session_id: str, output_dir: str, render_mode: str = "both"):
    """Run the full pipeline for a single session."""
    os.makedirs(output_dir, exist_ok=True)
    t0 = time.time()

    print(f"=== ag-02 Pipeline ===")
    print(f"Session: {session_id}")
    print(f"Output: {output_dir}")
    print(f"Render: {render_mode}")
    print()

    # Step 1: Parse
    print("[1/5] Parsing session from database...")
    session = get_session(session_id)
    print(f"  Title: {session.title}")
    print(f"  Parts: {len(session.parts)}")
    print(f"  Directory: {session.directory}")

    # Export raw data
    export_session_json(session, os.path.join(output_dir, "session.json"))
    print()

    # Step 2: Score & select
    print("[2/5] Scoring and selecting segments...")
    all_segments = group_into_segments(session.parts)
    print(f"  Raw segments: {len(all_segments)}")
    segments = select_top_segments(all_segments, target_count=5)
    print(f"  Selected: {len(segments)}")
    for s in segments:
        print(f"    [{s.label:12s}] score={s.score:.1f} parts={len(s.parts)} {s.display_text[:50]}")

    # Save segments
    import json
    seg_data = [
        {"index": s.index, "label": s.label, "score": s.score,
         "display_text": s.display_text, "part_count": len(s.parts)}
        for s in segments
    ]
    with open(os.path.join(output_dir, "segments.json"), "w") as f:
        json.dump(seg_data, f, indent=2, ensure_ascii=False)
    print()

    # Step 3: Generate narration script
    print("[3/5] Generating narration script...")
    script = generate_narration_script(segments, session.title)
    script_path = os.path.join(output_dir, "script.md")
    with open(script_path, "w") as f:
        f.write(script)
    print(f"  Saved: {script_path}")
    print()

    # Step 4: Generate TTS
    print("[4/5] Generating narration (MP3)...")
    audio_dir = os.path.join(output_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    audio_files = []

    for seg in segments:
        audio_path = os.path.join(audio_dir, f"seg_{seg.index:02d}.mp3")
        print(f"  Segment {seg.index} ({seg.label})...", end=" ")
        if generate_segment_narration(seg, session.title, audio_path):
            dur = get_audio_duration(audio_path)
            audio_files.append(audio_path)
            print(f"OK ({dur:.1f}s)")
        else:
            print("FAILED")

    # Combine all narration
    narration_path = os.path.join(output_dir, "narration.mp3")
    if combine_audio_files(audio_files, narration_path):
        total_dur = get_audio_duration(narration_path)
        print(f"  Combined: {total_dur:.1f}s -> {narration_path}")
    else:
        print("  ERROR: Failed to combine narration")
        return
    print()

    # Step 5: Render frames and compose
    render_modes = []
    if render_mode in ("terminal", "both"):
        render_modes.append("terminal")
    if render_mode in ("simple", "both"):
        render_modes.append("simple")

    for mode in render_modes:
        print(f"[5/5] Rendering ({mode}) and composing...")

        if mode == "terminal":
            from render_terminal import render_segment_frame
        else:
            from render_simple import render_segment_frame

        frames_dir = os.path.join(output_dir, f"frames_{mode}")
        os.makedirs(frames_dir, exist_ok=True)

        segment_frames = []
        for seg in segments:
            frame_path = os.path.join(frames_dir, f"seg_{seg.index:02d}.mp4")
            # Duration from audio if available, else default
            audio_path = os.path.join(audio_dir, f"seg_{seg.index:02d}.mp3")
            if os.path.exists(audio_path):
                dur = get_audio_duration(audio_path)
            else:
                dur = 10.0

            print(f"  Frame {seg.index} ({dur:.1f}s)...", end=" ")
            if render_segment_frame(seg, frame_path, dur):
                segment_frames.append({"frame": frame_path, "duration": dur})
                print("OK")
            else:
                print("FAILED")

        # Compose
        final_path = os.path.join(output_dir, f"final_{mode}.mp4")
        print(f"  Composing {len(segment_frames)} segments...")
        if compose_video(segment_frames, narration_path, final_path):
            size_mb = os.path.getsize(final_path) / (1024 * 1024)
            print(f"  DONE: {final_path} ({size_mb:.1f} MB)")
        else:
            print(f"  FAILED: {final_path}")
        print()

    elapsed = time.time() - t0
    print(f"=== Pipeline complete in {elapsed:.1f}s ===")


def main():
    parser = argparse.ArgumentParser(description="ag-02: Session to video")
    parser.add_argument("session_id", nargs="?", help="Session ID to process")
    parser.add_argument("-o", "--output", default="output", help="Output directory")
    parser.add_argument("--render", choices=["terminal", "simple", "both"], default="both")
    parser.add_argument("--list", action="store_true", help="List sessions")
    parser.add_argument("--list-dir", help="Filter sessions by directory")
    args = parser.parse_args()

    if args.list:
        sessions = list_sessions(args.list_dir)
        for s in sessions:
            print(f"{s['id']} | {s['parts']:4d} parts | {s['title'][:60]}")
        return

    if not args.session_id:
        parser.print_help()
        sys.exit(1)

    run_pipeline(args.session_id, args.output, args.render)


if __name__ == "__main__":
    main()
