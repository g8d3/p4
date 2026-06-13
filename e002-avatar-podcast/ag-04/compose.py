#!/usr/bin/env python3
"""Compose final 9:16 avatar podcast video with properly interleaved dialogue."""

import subprocess, os, re, tempfile, shutil

A_DURATION = 202.056
B_DURATION = 66.312
INTRO_DURATION = 4
OUTRO_DURATION = 4
W = 608
H = 1080
BG_CROP_X = 656

COLOR_A = '&H0000FFFF'
COLOR_B = '&H00FF00FF'
COLOR_W = '&H00FFFFFF'


def parse_script():
    path = os.path.join(os.path.dirname(__file__), '..', 'ag-02', 'script.md')
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


def build_subtitles(segments, tmpdir):
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
    for speaker, text, f_start, f_end, t_start, t_end in segments:
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
    in_a = os.path.join(os.path.dirname(__file__), '..', 'ag-03', 'persona_a.mp3')
    in_b = os.path.join(os.path.dirname(__file__), '..', 'ag-03', 'persona_b.mp3')
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


def compose_video(segments, ass_path, interleaved_audio, output):
    bg = 'podcast_bg.png'
    av_a = 'persona_a_avatar.png'
    av_b = 'persona_b_avatar.png'

    total_dur = segments[-1][5] if segments else 0

    a_times = []
    b_times = []
    for speaker, text, f_start, f_end, t_start, t_end in segments:
        if speaker == 'A':
            a_times.append(f"between(t,{t_start:.3f},{t_end:.3f})")
        else:
            b_times.append(f"between(t,{t_start:.3f},{t_end:.3f})")

    a_enable = '+'.join(a_times) if a_times else '0'
    b_enable = '+'.join(b_times) if b_times else '0'

    av_w = 200
    av_h = 200
    gap = 24
    total_av_w = 2 * av_w + gap
    av_x_offset = (W - total_av_w) // 2
    a_x = av_x_offset
    b_x = av_x_offset + av_w + gap
    av_y = 120

    hl_border = 5
    a_hl_x = a_x - hl_border
    b_hl_x = b_x - hl_border
    hl_y = av_y - hl_border
    hl_w = av_w + 2 * hl_border
    hl_h = av_h + 2 * hl_border

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-i', bg,
        '-loop', '1', '-i', av_a,
        '-loop', '1', '-i', av_b,
        '-i', interleaved_audio,
        '-filter_complex', (
            f"[0:v]crop={W}:{H}:{BG_CROP_X}:0,trim=duration={total_dur:.3f},format=yuv420p[bg];"
            f"[1:v]scale={av_w}:{av_h},format=rgba,setpts=PTS-STARTPTS[av1];"
            f"[2:v]scale={av_w}:{av_h},format=rgba,setpts=PTS-STARTPTS[av2];"
            f"[bg][av1]overlay=x={a_x}:y={av_y}[bg1];"
            f"[bg1][av2]overlay=x={b_x}:y={av_y}[vbase];"
            f"[vbase]drawbox=x={a_hl_x}:y={hl_y}:w={hl_w}:h={hl_h}:"
            f"color=blue@0.35:t=5:enable='{a_enable}'[v1];"
            f"[v1]drawbox=x={b_hl_x}:y={hl_y}:w={hl_w}:h={hl_h}:"
            f"color=magenta@0.35:t=5:enable='{b_enable}'[v2];"
            f"[v2]subtitles={ass_path}[vout]"
        ),
        '-map', '[vout]',
        '-map', '3:a',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-t', str(total_dur),
        output
    ]
    return cmd


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


def main():
    print("=== Video Composer (ag-04) ===")

    raw = parse_script()
    print(f"Parsed {len(raw)} dialogue segments from script.md")

    timed = estimate_timings(raw)
    total = timed[-1][5]
    print(f"Estimated total: {total:.2f}s")
    a_count = sum(1 for s in timed if s[0] == 'A')
    b_count = sum(1 for s in timed if s[0] == 'B')
    a_total = sum(s[3]-s[2] for s in timed if s[0] == 'A')
    b_total = sum(s[3]-s[2] for s in timed if s[0] == 'B')
    print(f"  A segments: {a_count}, B segments: {b_count}")
    print(f"  A total: {a_total:.2f}s, B total: {b_total:.2f}s")

    with tempfile.TemporaryDirectory() as tmpdir:
        print("\nBuilding subtitles...")
        ass_path = build_subtitles(timed, tmpdir)

        print("Splitting audio segments...")
        seg_files = split_audio_segments(timed, tmpdir)

        print("Interleaving audio in script order...")
        interleaved_audio = os.path.join(tmpdir, 'interleaved.mp3')
        concat_segments(seg_files, interleaved_audio, tmpdir)

        print("Composing main video...")
        main_vid = os.path.join(tmpdir, 'main.mp4')
        cmd = compose_video(timed, ass_path, interleaved_audio, main_vid)
        subprocess.run(cmd, check=True, capture_output=True)
        print("  Main video done")

        print("Creating intro card...")
        intro_vid = os.path.join(tmpdir, 'intro.mp4')
        create_title_card('title_intro.png', intro_vid, INTRO_DURATION, fade_out=True)

        print("Creating outro card...")
        outro_vid = os.path.join(tmpdir, 'outro.mp4')
        create_title_card('title_outro.png', outro_vid, OUTRO_DURATION, fade_in=True)

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

    print(f"\nDone! Output: video.mp4 ({W}x{H}, {total + INTRO_DURATION + OUTRO_DURATION:.1f}s)")


if __name__ == '__main__':
    main()
