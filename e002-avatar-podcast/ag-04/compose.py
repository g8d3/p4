#!/usr/bin/env python3
"""Compose final 9:16 avatar podcast video using Godot GPU rendering."""

import subprocess, os, re, tempfile, shutil, json, sys, math, shlex

A_DURATION = 202.056
B_DURATION = 66.312
INTRO_DURATION = 4
OUTRO_DURATION = 4
W = 608
H = 1080
FPS = 25
GODOT = os.path.expanduser('~/.local/bin/godot4')
GODOT_PROJECT = os.path.join(os.path.dirname(__file__), 'godot_project')
BG_CROP_X = (1920 - W) // 2  # 656

COLOR_A = '&H0000FFFF'
COLOR_B = '&H00FF00FF'
COLOR_W = '&H00FFFFFF'

AG02 = os.path.join(os.path.dirname(__file__), '..', 'ag-02')
AG03 = os.path.join(os.path.dirname(__file__), '..', 'ag-03')


def parse_script():
    path = os.path.join(AG02, 'script.md')
    segments = []
    with open(path) as f:
        for line in f:
            m = re.match(r'^([AB]):\s*(.*)', line.strip())
            if m:
                speaker = m.group(1)
                text = m.group(2).strip()
                if speaker and text:
                    segments.append((speaker, text))
    return segments


def estimate_timings(segments):
    a_total_chars = sum(len(t) for s, t in segments if s == 'A')
    b_total_chars = sum(len(t) for s, t in segments if s == 'B')
    a_used = 0.0
    b_used = 0.0
    timeline = 0.0
    timed = []
    for speaker, text in segments:
        chars = len(text)
        if speaker == 'A':
            dur = (chars / a_total_chars) * A_DURATION if a_total_chars else 0
            f_start = a_used
            a_used += dur
        else:
            dur = (chars / b_total_chars) * B_DURATION if b_total_chars else 0
            f_start = b_used
            b_used += dur
        f_end = f_start + dur
        t_start = timeline
        t_end = timeline + dur
        timed.append((speaker, text, f_start, f_end, t_start, t_end))
        timeline = t_end
    return timed


def build_timing_json(timed, output_dir):
    segs = []
    for speaker, text, f_start, f_end, t_start, t_end in timed:
        segs.append({
            "speaker": speaker,
            "start": round(t_start, 3),
            "end": round(t_end, 3),
            "text": text
        })

    godot_dir = GODOT_PROJECT
    total_dur = timed[-1][5] if timed else 0

    config = {
        "bg": "res://podcast_bg.png",
        "avatar_a": "res://persona_a_avatar.png",
        "avatar_b": "res://persona_b_avatar.png",
        "w": W,
        "h": H,
        "fps": FPS,
        "duration": round(total_dur, 3),
        "output_dir": output_dir,
        "segments": segs
    }
    return config


def copy_assets_to_godot():
    src = os.path.dirname(__file__)
    dst = GODOT_PROJECT
    for fname in ['podcast_bg.png', 'persona_a_avatar.png', 'persona_b_avatar.png']:
        shutil.copy2(os.path.join(src, fname), os.path.join(dst, fname))


def run_godot_renderer(config_path):
    cmd = [
        GODOT,
        '--path', GODOT_PROJECT,
        '--display-driver', 'x11',
        '--rendering-driver', 'opengl3',
        '--',
        config_path
    ]
    print(f"Running Godot renderer: {' '.join(shlex.quote(a) for a in cmd)}")
    result = subprocess.run(
        ['xvfb-run', '-a', '-s', '-screen 0 1920x1080x24'] + cmd,
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        raise RuntimeError(f"Godot renderer failed with code {result.returncode}")


def split_into_phrases(text):
    parts = re.split(r'(?<=[.?!;])\s+', text)
    result = []
    for p in parts:
        p = p.strip()
        if len(p) > 40:
            sub = re.split(r'(?<=[¿,])\s+|(?<=\,)\s+', p)
            result.extend(s.strip() for s in sub if s.strip())
        else:
            result.append(p)
    return result if result else [text]


def build_subtitles(timed, tmpdir):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,28,{COLOR_W},{COLOR_W},&H80000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,40,40,60,1
Style: A,Arial,30,{COLOR_A},{COLOR_A},&H80000000,&H00000000,1,0,0,0,100,100,0,0,1,2,1,2,40,40,60,1
Style: B,Arial,30,{COLOR_B},{COLOR_B},&H80000000,&H00000000,1,0,0,0,100,100,0,0,1,2,1,2,40,40,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for speaker, text, f_start, f_end, t_start, t_end in timed:
        phrases = split_into_phrases(text)
        phrase_dur = (t_end - t_start) / max(len(phrases), 1)
        style_name = 'A' if speaker == 'A' else 'B'
        for pi, phrase in enumerate(phrases):
            st = t_start + pi * phrase_dur
            et = st + phrase_dur * 0.95
            events.append(
                f"Dialogue: 0,{_fmt_ts(st)},{_fmt_ts(et)},{style_name},,0,0,0,,{phrase}"
            )
    path = os.path.join(tmpdir, 'subtitles.ass')
    with open(path, 'w') as f:
        f.write(header)
        f.write('\n'.join(events))
        f.write('\n')
    return path


def _fmt_ts(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


def split_audio_segments(timed, tmpdir):
    in_a = os.path.join(AG03, 'persona_a.mp3')
    in_b = os.path.join(AG03, 'persona_b.mp3')
    seg_files = []
    for i, (speaker, text, f_start, f_end, t_start, t_end) in enumerate(timed):
        inp = in_a if speaker == 'A' else in_b
        out = os.path.join(tmpdir, f'seg_{i:03d}_{speaker}.mp3')
        dur = max(f_end - f_start, 0.01)
        subprocess.run([
            'ffmpeg', '-y', '-i', inp,
            '-ss', str(f_start), '-t', str(dur),
            '-c', 'copy', out
        ], check=True, capture_output=True)
        seg_files.append(out)
    return seg_files


def concat_segments(seg_files, output, tmpdir):
    concat_file = os.path.join(tmpdir, 'concat.txt')
    with open(concat_file, 'w') as f:
        for sf in seg_files:
            f.write(f"file '{sf}'\n")
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', concat_file, '-c', 'copy', output
    ], check=True, capture_output=True)


def create_title_card(bg_img, output, duration, fade_out=True, fade_in=False):
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
        '-loop', '1', '-i', bg_img,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '128k',
        '-t', str(duration),
    ]
    vf = f"crop={W}:{H}:{BG_CROP_X}:0"
    if fade_out:
        vf += f",fade=t=out:st={duration-1}:d=1"
    if fade_in:
        vf += ",fade=t=in:st=0:d=1"
    cmd += ['-vf', vf, '-shortest', output]
    subprocess.run(cmd, check=True, capture_output=True)


def compose_final_video(frames_dir, num_frames, ass_path, interleaved_audio, total_dur, output):
    frame_pattern = os.path.join(frames_dir, 'frame_%05d.png')
    actual_dur = num_frames / FPS

    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(FPS),
        '-i', frame_pattern,
        '-i', interleaved_audio,
        '-filter_complex',
        f"[0:v]subtitles={ass_path}[vout]",
        '-map', '[vout]',
        '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-t', str(total_dur),
        output
    ]
    print(f"Composing final video: {' '.join(shlex.quote(a) for a in cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg stderr:", result.stderr)
        raise RuntimeError(f"FFmpeg failed: {result.returncode}")
    return output


def main():
    print("=== Video Composer (ag-04) — Godot GPU Render ===")

    # 1. Parse script and build timings
    raw = parse_script()
    print(f"Parsed {len(raw)} dialogue segments from script.md")

    timed = estimate_timings(raw)
    total_dur = timed[-1][5]
    print(f"Estimated total: {total_dur:.2f}s")
    a_count = sum(1 for s in timed if s[0] == 'A')
    b_count = sum(1 for s in timed if s[0] == 'B')
    a_total = sum(s[3]-s[2] for s in timed if s[0] == 'A')
    b_total = sum(s[3]-s[2] for s in timed if s[0] == 'B')
    print(f"  A segments: {a_count}, B segments: {b_count}")
    print(f"  A total: {a_total:.2f}s, B total: {b_total:.2f}s")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 2. Copy assets into Godot project
        print("\nCopying assets to Godot project...")
        copy_assets_to_godot()

        # 3. Build timing JSON for Godot
        print("Building timing JSON for Godot...")
        frames_dir = os.path.join(tmpdir, 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        timing_config = build_timing_json(timed, frames_dir)
        config_path = os.path.join(tmpdir, 'render_config.json')
        with open(config_path, 'w') as f:
            json.dump(timing_config, f, indent=2)

        # 4. Run Godot renderer
        print("Running Godot GPU renderer...")
        run_godot_renderer(config_path)

        # Count frames
        frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
        num_frames = len(frame_files)
        print(f"Godot produced {num_frames} frames")
        if num_frames == 0:
            raise RuntimeError("Godot produced no frames!")

        # 5. Build subtitles
        print("Building subtitles...")
        ass_path = build_subtitles(timed, tmpdir)

        # 6. Split and interleave audio
        print("Splitting audio segments...")
        seg_files = split_audio_segments(timed, tmpdir)
        print("Interleaving audio in script order...")
        interleaved_audio = os.path.join(tmpdir, 'interleaved.mp3')
        concat_segments(seg_files, interleaved_audio, tmpdir)
        print(f"Interleaved audio at {interleaved_audio}")

        # 7. Compose main video from Godot frames + audio + subtitles
        print("Composing main video...")
        main_vid = os.path.join(tmpdir, 'main.mp4')
        compose_final_video(frames_dir, num_frames, ass_path, interleaved_audio, total_dur, main_vid)

        # 8. Create intro and outro cards
        print("Creating intro card...")
        intro_vid = os.path.join(tmpdir, 'intro.mp4')
        create_title_card('title_intro.png', intro_vid, INTRO_DURATION, fade_out=True)

        print("Creating outro card...")
        outro_vid = os.path.join(tmpdir, 'outro.mp4')
        create_title_card('title_outro.png', outro_vid, OUTRO_DURATION, fade_in=True)

        # 9. Concatenate intro + main + outro
        print("Concatenating intro + main + outro...")
        final = os.path.join(tmpdir, 'final.mp4')
        subprocess.run([
            'ffmpeg', '-y',
            '-i', intro_vid,
            '-i', main_vid,
            '-i', outro_vid,
            '-filter_complex',
            '[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[outv][outa]',
            '-map', '[outv]', '-map', '[outa]',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            final
        ], check=True, capture_output=True)

        shutil.move(final, 'video.mp4')

    print(f"\nDone! Output: video.mp4 ({W}x{H}, {total_dur + INTRO_DURATION + OUTRO_DURATION:.1f}s)")


if __name__ == '__main__':
    main()
