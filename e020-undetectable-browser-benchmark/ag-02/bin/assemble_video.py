#!/usr/bin/env python3
"""Assemble the session video from the 16-scene storyboard.

Each scene shows its image for a fixed duration; the full narration audio plays
underneath with combined subtitles. Usage: python3 assemble_video.py
"""
import re, subprocess, os, json

OUT = os.path.join(os.path.dirname(__file__), "..", "output", "undetectable-browsers-google")
ASSETS = os.path.join(OUT, "assets")
AUDIO = os.path.join(OUT, "audio")
FPS = 25

# 16 scenes (storyboard order). Duration per scene in seconds.
SCENES = [
    ("sb-ai-title.jpg",           3.0),
    ("sb-slide-hook.png",         3.0),
    ("sb-slide-browsers.png",     3.0),
    ("scene-results.png",         3.0),
    ("sb-slide-cdp.png",          3.0),
    ("sb-slide-marionette.png",   3.0),
    ("sb-slide-juggler.png",      3.0),
    ("sb-slide-bidi.png",         3.0),
    ("sb-shot-search.png",        3.0),
    ("sb-ai-nocaptcha.jpg",       3.0),
    ("sb-shot-auth.png",          3.0),
    ("sb-slide-keyfinding.png",   3.0),
    ("sb-slide-puppeteer.png",    3.0),
    ("sb-ai-theft.jpg",           3.0),
    ("sb-slide-recommend.png",    3.0),
    ("sb-ai-outro.jpg",           3.0),
]

# Narration audio (concatenated, in order)
NARRATION = ["scene1.mp3", "scene2.mp3", "scene3.mp3", "scene4.mp3"]
# Per-narration-part SRTs (for subtitles)
NARR_SRT = ["mono1.srt", "mono2.srt", "mono3.srt", "mono4.srt"]

# Parakeet quirks → correct word (brand names it mishears)
CORRECTIONS = {
    "capture": "captcha", "capta": "captcha", "camofox": "Camoufox",
    "puppeter": "Puppeteer", "google": "Google", "chrome": "Chrome",
    "firefox": "Firefox", "playwright": "Playwright", "juggler": "Juggler",
    "marionette": "Marionette", "cdp": "CDP", "cdp.": "CDP",
}

def fix_srt(path):
    content = open(path).read()
    for wrong, right in CORRECTIONS.items():
        content = re.sub(r'\b' + re.escape(wrong) + r'\b', right, content, flags=re.IGNORECASE)
    open(path, 'w').write(content)

def srt_shift(srt_in, srt_out, offset_sec):
    """Shift an SRT by offset_sec seconds."""
    def fmt(t):
        h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"
    out = []
    for line in open(srt_in).read().splitlines():
        m = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})", line)
        if m:
            a = int(m[1])*3600 + int(m[2])*60 + int(m[3]) + int(m[4])/1000 + offset_sec
            b = int(m[5])*3600 + int(m[6])*60 + int(m[7]) + int(m[8])/1000 + offset_sec
            out.append(f"{fmt(a)} --> {fmt(b)}")
        else:
            out.append(line)
    open(srt_out, 'w').write('\n'.join(out))

def build_scene(i, img, dur, workdir):
    vf = "scale=608:1080,format=yuv420p"
    out = os.path.join(workdir, f"sc{i}.mp4")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1',
        '-i', os.path.join(ASSETS, img), '-vf', vf, '-t', str(dur), '-r', str(FPS), out], check=True)
    return out

def main():
    workdir = os.path.join(OUT, "parts")
    os.makedirs(workdir, exist_ok=True)

    # 1. Build each scene clip
    clips = []
    for i, (img, dur) in enumerate(SCENES):
        clips.append(build_scene(i, img, dur, workdir))

    # 2. Concat clips
    lst = os.path.join(workdir, "list.txt")
    with open(lst, 'w') as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    video = os.path.join(workdir, "video_novid.mp4")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat',
        '-safe', '0', '-i', lst, '-c', 'copy', video], check=True)

    # 3. Concatenate narration audio
    alst = os.path.join(workdir, "alist.txt")
    with open(alst, 'w') as f:
        for n in NARRATION:
            f.write(f"file '{os.path.join(AUDIO, n)}'\n")
    audio = os.path.join(workdir, "full_audio.mp3")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat',
        '-safe', '0', '-i', alst, '-c', 'copy', audio], check=True)

    # 4. Combine SRTs with offsets (narration part durations)
    combined2 = os.path.join(workdir, "combined2.srt")
    with open(combined2, 'w') as f:
        idx = 1
        total = 0.0
        for n, srt in zip(NARRATION, NARR_SRT):
            fix_srt(os.path.join(AUDIO, srt))
            shifted = os.path.join(workdir, f"shift_{n}.srt")
            srt_shift(os.path.join(AUDIO, srt), shifted, total)
            dur = float(json.loads(subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_entries', 'format=duration', os.path.join(AUDIO, n)],
                capture_output=True, text=True).stdout)['format']['duration'])
            for line in open(shifted):
                if re.match(r'^\d+$', line.strip()):
                    f.write(str(idx) + '\n'); idx += 1
                else:
                    f.write(line)
            total += float(dur)

    # 5. Burn subtitles + mux audio
    subs = os.path.join(workdir, "video_sub.mp4")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', video,
        '-vf', f"subtitles={combined2}:force_style='FontSize=14,FontName=Inter,Alignment=2,MarginV=40'",
        '-c:v', 'libx264', subs], check=True)

    final = os.path.join(OUT, "FINAL.mp4")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', subs,
        '-i', audio, '-c:v', 'copy', '-c:a', 'aac', '-shortest', final], check=True)
    print(f"DONE: {final}")

if __name__ == '__main__':
    main()
