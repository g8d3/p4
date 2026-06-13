#!/usr/bin/env python3
"""Generate the podcast video with alternating avatars."""

import subprocess, json, math, os, tempfile

A_DURATION = 202.056
B_DURATION = 66.312
TOTAL_DURATION = A_DURATION + B_DURATION  # 268.368s

INTRO_DURATION = 5
OUTRO_DURATION = 5

# Speaker sequence (A = persona_a, B = persona_b)
SEQUENCE = [
    'A','B','A','B','A',                    # Intro
    'B','A','B','A','B','A',               # Topic 1
    'A','B','A','B','A','B','A',           # Topic 2
    'A','B','A','B','A','B','A',           # Topic 3
    'A','B','A','B','A','B','A',           # Topic 4
    'B','A','B','A',                       # Topic 5
    'A','B','A','B','B','A','A','B','A','B','A',  # Closing
]

def estimate_timings():
    """Estimate start/end times for each segment.
    Returns list of (speaker, file_start, file_end, timeline_start, timeline_end).
    file_start/file_end are offsets within the speaker's audio file.
    timeline_start/timeline_end are positions in the final combined timeline.
    """
    a_count = SEQUENCE.count('A')
    b_count = SEQUENCE.count('B')
    a_per_seg = A_DURATION / a_count   # seconds per A segment in A's audio file
    b_per_seg = B_DURATION / b_count   # seconds per B segment in B's audio file

    a_used = 0.0
    b_used = 0.0
    timeline = 0.0
    segments = []

    for speaker in SEQUENCE:
        if speaker == 'A':
            dur = a_per_seg
            f_start = a_used
            a_used += dur
        else:
            dur = b_per_seg
            f_start = b_used
            b_used += dur

        f_end = f_start + dur
        t_start = timeline
        t_end = timeline + dur
        segments.append((speaker, f_start, f_end, t_start, t_end))
        timeline = t_end

    return segments

def make_video_segment(segments, tmpdir):
    """Create a single video by overlaying correct avatars per segment."""
    a_vid_enable = []
    b_vid_enable = []
    a_aud_enable = []
    b_aud_enable = []

    for i, (speaker, f_start, f_end, t_start, t_end) in enumerate(segments):
        # Video overlay uses timeline positions
        if speaker == 'A':
            a_vid_enable.append(f"between(t,{t_start:.3f},{t_end:.3f})")
        else:
            b_vid_enable.append(f"between(t,{t_start:.3f},{t_end:.3f})")

        # Audio selection uses file offset positions
        if speaker == 'A':
            a_aud_enable.append(f"between(t,{f_start:.3f},{f_end:.3f})")
        else:
            b_aud_enable.append(f"between(t,{f_start:.3f},{f_end:.3f})")

    a_vid_expr = '+'.join(a_vid_enable)
    b_vid_expr = '+'.join(b_vid_enable)
    a_aud_expr = '+'.join(a_aud_enable)
    b_aud_expr = '+'.join(b_aud_enable)

    bg_file = 'podcast_bg.png'
    av_a_file = 'persona_a_avatar.png'
    av_b_file = 'persona_b_avatar.png'
    audio_a = '../ag-03/persona_a.mp3'
    audio_b = '../ag-03/persona_b.mp3'

    total = TOTAL_DURATION

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-i', bg_file,
        '-loop', '1', '-i', av_a_file,
        '-loop', '1', '-i', av_b_file,
        '-i', audio_a,
        '-i', audio_b,
        '-filter_complex', (
            f"[0:v]scale=1920:1080,trim=duration={total:.3f},format=yuv420p[bg];"
            f"[1:v]scale=320:320,format=rgba,zoompan=z='zoom+0.001':d=125,setpts=PTS-STARTPTS,"
            f"fade=t=in:st=0:d=0.5,fade=t=out:st={total-0.5:.3f}:d=0.5[av1];"
            f"[2:v]scale=320:320,format=rgba,zoompan=z='zoom+0.001':d=125,setpts=PTS-STARTPTS,"
            f"fade=t=in:st=0:d=0.5,fade=t=out:st={total-0.5:.3f}:d=0.5[av2];"
            f"[bg][av1]overlay=x=240:y=280:enable='{a_vid_expr}'[bg1];"
            f"[bg1][av2]overlay=x=1360:y=280:enable='{b_vid_expr}'[vout];"
            f"[3:a]aselect='{a_aud_expr}',asetpts=N/SR/TB[a_sel];"
            f"[4:a]aselect='{b_aud_expr}',asetpts=N/SR/TB[b_sel];"
            f"[a_sel][b_sel]concat=n=2:v=0:a=1[aout]"
        ),
        '-map', '[vout]',
        '-map', '[aout]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-t', str(total),
        'tmp_video.mp4'
    ]

    print("Running ffmpeg composition...")
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    if result.stderr:
        for line in result.stderr.strip().split('\n')[-5:]:
            print(f"  {line}")
    return 'tmp_video.mp4'

def add_intro_outro(video_file, output_file):
    """Add intro and outro title cards using concat filter."""
    total_dur = TOTAL_DURATION
    with tempfile.TemporaryDirectory() as tmp:
        intro_vid = os.path.join(tmp, 'intro.mp4')
        outro_vid = os.path.join(tmp, 'outro.mp4')

        print("  Creating intro card...")
        subprocess.run([
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
            '-loop', '1', '-i', 'title_intro.png',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k',
            '-t', str(INTRO_DURATION),
            '-vf', 'fade=t=out:st=4:d=1',
            '-shortest', intro_vid
        ], check=True, capture_output=True)

        print("  Creating outro card...")
        subprocess.run([
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
            '-loop', '1', '-i', 'title_outro.png',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k',
            '-t', str(OUTRO_DURATION),
            '-vf', 'fade=t=in:st=0:d=1',
            '-shortest', outro_vid
        ], check=True, capture_output=True)

        print("  Concatenating intro + main + outro...")
        subprocess.run([
            'ffmpeg', '-y',
            '-i', intro_vid,
            '-i', video_file,
            '-i', outro_vid,
            '-filter_complex',
            '[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[outv][outa]',
            '-map', '[outv]', '-map', '[outa]',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            output_file
        ], check=True, capture_output=True)

def add_subtitles(video_file):
    """Add TikTok-style subtitles in Spanish."""
    # Generate subtitle text from script lines with estimated timings
    script_lines = [
        (0, 5, "P4 PODCAST"),
        (5, 10, "¿Has oído hablar de p4?"),
        (10, 15, "¿Otro framework más de inteligencia artificial?"),
        (15, 25, "p4 es un sistema donde los agentes de IA\nse comunican usando archivos y carpetas."),
        (25, 30, "¿Archivos? ¿Como los que tengo en mi computadora?"),
        (30, 40, "Imagina agentes que dejan mensajes\nen archivos de texto..."),
        # Approximate subtitles for the rest
    ]

    srt_lines = []
    idx = 1
    for start, end, text in script_lines:
        start_ts = f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{start%60:06.3f}".replace('.', ',')
        end_ts = f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{end%60:06.3f}".replace('.', ',')
        srt_lines.append(f"{idx}")
        srt_lines.append(f"{start_ts} --> {end_ts}")
        srt_lines.append(text)
        srt_lines.append("")
        idx += 1

    srt_path = 'subtitles.srt'
    with open(srt_path, 'w') as f:
        f.write('\n'.join(srt_lines))

    output = video_file.replace('.mp4', '_subs.mp4')
    subprocess.run([
        'ffmpeg', '-y',
        '-i', video_file,
        '-vf', f"subtitles={srt_path}:force_style='Alignment=2,FontSize=14,FontName=Arial,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1,MarginV=40'",
        '-c:a', 'copy',
        output
    ], check=True, capture_output=True)
    return output

def main():
    segments = estimate_timings()

    print(f"Total segments: {len(segments)}")
    print(f"A segments: {sum(1 for s in segments if s[0]=='A')}")
    print(f"B segments: {sum(1 for s in segments if s[0]=='B')}")
    print(f"Estimated total: {segments[-1][4]:.2f}s")

    # Step 1: Compose main video with alternating avatars
    print("\nStep 1: Composing main video...")
    main_video = make_video_segment(segments, '.')

    # Step 2: Add intro and outro
    print("\nStep 2: Adding intro/outro...")
    add_intro_outro(main_video, 'output_video.mp4')

    # Step 3: Add subtitles
    print("\nStep 3: Adding subtitles...")
    final = add_subtitles('output_video.mp4')

    os.rename(final, 'video.mp4')
    print(f"\nDone! Output: video.mp4")

    # Cleanup
    for f in ['tmp_video.mp4', 'output_video.mp4', 'tmp_video_subs.mp4', 'output_video_subs.mp4', 'subtitles.srt']:
        if os.path.exists(f):
            os.remove(f)

if __name__ == '__main__':
    main()
