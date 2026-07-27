#!/usr/bin/env python3
"""
AI News Video Pipeline — full automation from script to final MP4.

Usage:
  python3 pipeline.py output/script.md

Reads the script (with [EMOTION TAGS]), generates TTS, aligns subtitles,
downloads stock videos from Pixabay, and assembles the final video.

Requirements:
  - model_worker.py running (Parakeet ASR server, /tmp/transcribe-worker.sock)
  - Chrome running with CDP on port 9222 (for Pixabay downloads)
  - edge-tts, ffmpeg installed
"""
import subprocess, json, os, sys, re, time, shutil
from pathlib import Path
from difflib import SequenceMatcher

BASE = Path(__file__).parent.parent
OUTPUT = BASE / 'output'
WORKER_SOCKET = '/tmp/transcribe-worker.sock'
CHROME_PORT = 9222
TMPDIR = Path('/tmp/ai-news-build')

# Visual search terms for Pixabay — one per expected sentence in the script
SEARCH_TERMS = [
    "globe network animation",
    "neural network technology", 
    "cyber security shield",
    "security guardrails protection",
    "artificial intelligence escape",
    "network connection technology",
    "cyber security containment",
    "debate controversy balance",
    "stage spotlights event",
    "question mark abstract",
    "portal light beam opening",
    "smartphone technology",
    "brain computer interface",
    "bar chart graph business",
    "money counting numbers",
    "blocks structure chain",
    "magnifying glass search",
    "scanning forensic technology",
    "data stream matrix code",
    "fast motion speed lines",
    "colorful abstract art",
    "light flash burst",
    "merging particles connection",
    "abstract lines converging",
    "expanding rings circles",
]

def log(msg):
    print(f"[pipeline] {msg}", flush=True)

def check_deps():
    """Verify required services are running."""
    if not os.path.exists(WORKER_SOCKET):
        log(f"ERROR: Worker socket not found at {WORKER_SOCKET}")
        log("Start model_worker.py first!")
        sys.exit(1)
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('127.0.0.1', CHROME_PORT))
        s.close()
    except:
        log(f"ERROR: Chrome not running on port {CHROME_PORT}")
        log("Start: google-chrome --headless --remote-debugging-port=9222 ...")
        sys.exit(1)
    for cmd in ['edge-tts', 'ffmpeg', 'agent-browser']:
        if not shutil.which(cmd):
            log(f"ERROR: {cmd} not found")
            sys.exit(1)
    log("All dependencies OK")

def generate_tts(script_path, output_path):
    """Generate TTS from script using edge-tts."""
    log("Generating TTS...")
    # Extract clean text (remove tags)
    with open(script_path) as f:
        text = re.sub(r'\[.*?\]', '', f.read())
    text = re.sub(r'\s+', ' ', text).strip()
    txt_path = output_path.with_suffix('.txt')
    with open(txt_path, 'w') as f:
        f.write(text + '\n')
    subprocess.run([
        'edge-tts', '--voice', 'en-US-GuyNeural',
        '-f', str(txt_path),
        '--write-media', str(output_path)
    ], check=True, timeout=300)
    dur = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries',
        'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
        str(output_path)], capture_output=True, text=True)
    log(f"TTS: {output_path.name} ({float(dur.stdout.strip()):.0f}s)")

def align_subtitles(audio_path, script_path):
    """Transcribe audio with Parakeet, align with script text → SRT + manifest."""
    log("Transcribing & aligning...")
    result = call_worker(audio_path)
    
    # Parse script
    raw = script_path.read_text()
    tag_pat = re.compile(r'(\[[A-Za-z\s]+\])')
    sentences = []
    current_tags = []
    for line in raw.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        line_tags = tag_pat.findall(line)
        if line_tags:
            current_tags.extend(line_tags)
        chunks = re.split(r'\[(?:PAUSE|DRAMATIC PAUSE)\]', line)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            clean = tag_pat.sub('', chunk).strip()
            if not clean:
                continue
            for s in re.split(r'(?<=[.!?])\s+', clean):
                s = s.strip()
                if s:
                    sentences.append({'text': s, 'tags': list(current_tags) if current_tags else []})
        current_tags = []

    words_raw = result.get('words_raw', [])
    probe_words = [w['text'].lower() for w in words_raw]
    
    # Align & chunk
    def words_from_text(text):
        return re.findall(r"[a-z0-9']+", text.lower())
    
    srt_segments = []
    manifest_segments = []
    idx = 0
    for entry in sentences:
        sent = entry['text']
        sent_w = words_from_text(sent)
        if not sent_w:
            continue
        n = len(sent_w)
        best_off = 0
        best_r = 0
        for off in range(-5, 6):
            start = max(0, idx + off)
            if start + n > len(probe_words):
                continue
            r = SequenceMatcher(None, sent_w, probe_words[start:start+n]).ratio()
            if r > best_r:
                best_r, best_off = r, off
        ai = max(0, idx + best_off)
        matched = words_raw[ai:ai+n]
        if not matched:
            idx += 1
            continue
        # Chunk into ~5 word subtitle groups
        chunks_w = [matched[i:i+5] for i in range(0, len(matched), 5)]
        for cw in chunks_w:
            srt_segments.append({
                'start': cw[0]['start'],
                'end': cw[-1]['end'],
                'text': ' '.join(w['text'] for w in cw)
            })
        manifest_segments.append({
            'text': sent, 'tags': entry['tags'],
            'start': matched[0]['start'], 'end': matched[-1]['end']
        })
        idx = ai + n

    # Write SRT
    def fmt_time(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = sec % 60
        return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')
    
    srt_path = audio_path.with_suffix('.srt')
    with open(srt_path, 'w') as f:
        for i, seg in enumerate(srt_segments, 1):
            f.write(f"{i}\n{fmt_time(seg['start'])} --> {fmt_time(seg['end'])}\n{seg['text']}\n\n")

    manifest_path = audio_path.with_suffix('.manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest_segments, f, indent=2)
    
    log(f"SRT: {srt_path} ({len(srt_segments)} segments)")
    log(f"Manifest: {manifest_path} ({len(manifest_segments)} sentences)")
    return srt_path, manifest_path

def call_worker(audio_path):
    import socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(120)
    sock.connect(WORKER_SOCKET)
    sock.sendall(json.dumps({'path': str(audio_path)}).encode())
    sock.shutdown(socket.SHUT_WR)
    data = b''
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        data += chunk
    sock.close()
    return json.loads(data)

def download_videos(manifest_path):
    """Download one video per segment from Pixabay."""
    with open(manifest_path) as f:
        segments = json.load(f)
    
    n_seg = min(len(segments), len(SEARCH_TERMS))
    TMPDIR.mkdir(parents=True, exist_ok=True)
    
    for i in range(n_seg):
        term = SEARCH_TERMS[i]
        out = TMPDIR / f'seg_{i}.webm'
        
        if out.exists() and out.stat().st_size > 1000:
            log(f"  [{i+1}/{n_seg}] Cached: {term}")
            continue
        
        seg = segments[i]
        dur = round(seg['end'] - seg['start'] + 0.2, 2)
        
        log(f"  [{i+1}/{n_seg}] Downloading: {term} ({dur}s)")
        
        # Search Pixabay
        import urllib.parse
        search_url = f"https://pixabay.com/videos/search/{urllib.parse.quote(term)}/"
        subprocess.run(['agent-browser', '--auto-connect', 'open', search_url],
                      capture_output=True, timeout=30)
        time.sleep(2)
        
        # Click first download button
        snap = subprocess.run(['agent-browser', '--auto-connect', 'snapshot', '-i'],
                            capture_output=True, text=True, timeout=20)
        download_ref = None
        for line in snap.stdout.split('\n'):
            if 'Download' in line and 'ref=' in line:
                m = re.search(r'ref=([a-z0-9]+)', line)
                if m:
                    download_ref = m.group(1)
                    break
        
        if not download_ref:
            log(f"    No download found for '{term}', trying fallback...")
            # Try simpler search
            simple = term.split()[0]
            search_url2 = f"https://pixabay.com/videos/search/{simple}/"
            subprocess.run(['agent-browser', '--auto-connect', 'open', search_url2],
                          capture_output=True, timeout=30)
            time.sleep(2)
            snap2 = subprocess.run(['agent-browser', '--auto-connect', 'snapshot', '-i'],
                                 capture_output=True, text=True, timeout=20)
            for line in snap2.stdout.split('\n'):
                if 'Download' in line and 'ref=' in line:
                    m = re.search(r'ref=([a-z0-9]+)', line)
                    if m:
                        download_ref = m.group(1)
                        break
        
        if not download_ref:
            log(f"    SKIP: no download for '{term}'")
            continue
        
        subprocess.run(['agent-browser', '--auto-connect', 'click', f'@{download_ref}'],
                      capture_output=True, timeout=30)
        time.sleep(3)
        
        # Find newest file in ~/Downloads
        dl_dir = Path.home() / 'Downloads'
        mp4s = sorted(dl_dir.glob('*.mp4'), key=os.path.getmtime, reverse=True)
        if not mp4s:
            log(f"    SKIP: no file downloaded for '{term}'")
            continue
        latest = mp4s[0]
        
        # Convert to WebM + scale to portrait
        subprocess.run(['ffmpeg', '-y', '-i', str(latest), '-t', str(dur),
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
            '-c:v', 'libvpx', '-b:v', '2M', '-c:a', 'libvorbis', str(out)],
            capture_output=True, timeout=120)
        
        log(f"    Saved: {out.name} ({out.stat().st_size//1024}KB)")

def build_video(manifest_path, srt_path, audio_path, output_path):
    """Concatenate all video segments, burn subtitles, merge audio."""
    with open(manifest_path) as f:
        segments = json.load(f)
    
    n_seg = min(len(segments), len(SEARCH_TERMS))
    
    # Build concat file
    concat_file = TMPDIR / 'concat.txt'
    with open(concat_file, 'w') as f:
        for i in range(n_seg):
            seg_file = TMPDIR / f'seg_{i}.webm'
            if seg_file.exists():
                f.write(f"file {seg_file}\n")
    
    total_dur = round(segments[-1]['end'] + 0.3, 2)
    
    log(f"Concat: {n_seg} segments, {total_dur}s total")
    
    subprocess.run([
        'ffmpeg',
        '-f', 'concat', '-safe', '0', '-i', str(concat_file),
        '-i', str(audio_path),
        '-vf', f"subtitles={srt_path}:force_style='FontSize=18,PrimaryColour=&H00FFFFFF,BorderStyle=1,Outline=2,MarginV=50'",
        '-map', '0:v', '-map', '1:a',
        '-t', str(total_dur),
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
        '-c:a', 'aac', '-b:a', '128k',
        str(output_path), '-y'
    ], check=True, timeout=600)
    
    log(f"FINAL: {output_path}")

def run(script_path):
    script_path = Path(script_path)
    audio_path = OUTPUT / f"{script_path.stem}.mp3"
    output_path = OUTPUT / "FINAL.mp4"
    
    TMPDIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    
    check_deps()
    generate_tts(script_path, audio_path)
    srt_path, manifest_path = align_subtitles(audio_path, script_path)
    download_videos(manifest_path)
    build_video(manifest_path, srt_path, audio_path, output_path)
    
    # Verify
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_entries', 'format=duration,size', '-show_streams', str(output_path)],
        capture_output=True, text=True)
    info = json.loads(r.stdout)
    dur = info['format']['duration']
    size = int(info['format']['size'])
    v = [s for s in info['streams'] if s['codec_type']=='video'][0]
    a = [s for s in info['streams'] if s['codec_type']=='audio'][0]
    log(f"OK: {output_path.name}")
    log(f"  Duration: {float(dur):.1f}s | Size: {size/1024/1024:.1f}MB")
    log(f"  Video: {v['width']}x{v['height']} @ {v.get('r_frame_rate','?')}fps")
    log(f"  Audio: {a['codec_name']} @ {a.get('sample_rate','?')}Hz")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <script.md>")
        sys.exit(1)
    run(sys.argv[1])
