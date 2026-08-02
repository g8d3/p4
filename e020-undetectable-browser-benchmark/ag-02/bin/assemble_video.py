#!/usr/bin/env python3
"""Assemble the session video: scenes → Ken Burns → subtitles → concat.

Usage: python3 assemble_video.py
Expects in output/: scene1..4.mp3, mono1..4.srt, scene-*.png
"""
import re, subprocess, os, sys, json

OUT = os.path.join(os.path.dirname(__file__), "..", "output")
FPS = 25
W, H = 608, 1080

# Parakeet quirks → correct word (brand names it mishears)
CORRECTIONS = {
    "capture": "captcha",
    "capta": "captcha",
    "camofox": "Camoufox",
    "camuflaje": "Camoufox",
    "puppeter": "Puppeteer",
    "google": "Google",
    "chrome": "Chrome",
    "firefox": "Firefox",
    "playwright": "Playwright",
    "juggler": "Juggler",
    "marionette": "Marionette",
    "cdp": "CDP",
    "cdp.": "CDP",
}

SCENES = [
    {"img": "scene-title.png",    "audio": "mono1.mp3", "srt": "mono1.srt"},
    {"img": "scene-protocols.png", "audio": "mono2.mp3", "srt": "mono2.srt"},
    {"img": "scene-results.png",  "audio": "mono3.mp3", "srt": "mono3.srt"},
    {"img": "scene-findings.png", "audio": "mono4.mp3", "srt": "mono4.srt"},
]

def fix_srt(path):
    """Apply word corrections in-place to an SRT."""
    content = open(path).read()
    for wrong, right in CORRECTIONS.items():
        content = re.sub(r'\b' + re.escape(wrong) + r'\b', right, content, flags=re.IGNORECASE)
    open(path, 'w').write(content)

def audio_duration(path):
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_entries', 'format=duration', path], capture_output=True, text=True)
    return float(json.loads(r.stdout)['format']['duration'])

def build_scene(i, scene, workdir):
    img = os.path.join(OUT, scene["img"])
    audio = os.path.join(OUT, scene["audio"])
    srt = os.path.join(OUT, scene["srt"])
    fix_srt(srt)

    dur = audio_duration(audio)
    frames = int(dur * FPS)

    # Ken Burns zoompan on 608x1080
    vf = (
        f"scale=1216:2160,"
        f"zoompan=z='1.0+0.008*on':d={frames}:fps={FPS}:s={W}x{H},"
        f"format=yuv420p"
    )
    video = os.path.join(workdir, f"scene{i}_novid.mp4")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1',
        '-i', img, '-vf', vf, '-t', str(dur), video], check=True)

    # Burn subtitles
    subs = os.path.join(workdir, f"scene{i}.mp4")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', video,
        '-vf', f"subtitles={srt}:force_style='FontSize=14,FontName=Inter,Alignment=2,MarginV=40'",
        subs], check=True)
    return subs

def main():
    workdir = os.path.join(OUT, "parts")
    os.makedirs(workdir, exist_ok=True)

    parts = []
    for i, scene in enumerate(SCENES, 1):
        print(f"Building scene {i}...", flush=True)
        parts.append(build_scene(i, scene, workdir))

    print("Concatenating...", flush=True)
    concat_file = os.path.join(workdir, "list.txt")
    with open(concat_file, 'w') as f:
        for p in parts:
            f.write(f"file '{p}'\n")

    final_novid = os.path.join(OUT, "final_novid.mp4")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat',
        '-safe', '0', '-i', concat_file, '-c', 'copy', final_novid], check=True)

    print("Muxing audio...", flush=True)
    # Concatenate scene audio
    audio_concat = os.path.join(workdir, "audio_list.txt")
    with open(audio_concat, 'w') as f:
        for scene in SCENES:
            f.write(f"file '{os.path.join(OUT, scene['audio'])}'\n")
    full_audio = os.path.join(workdir, "full_audio.mp3")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat',
        '-safe', '0', '-i', audio_concat, '-c', 'copy', full_audio], check=True)

    final = os.path.join(OUT, "FINAL.mp4")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', final_novid,
        '-i', full_audio, '-c:v', 'copy', '-c:a', 'aac', '-shortest', final], check=True)
    print(f"DONE: {final}")

if __name__ == '__main__':
    main()
