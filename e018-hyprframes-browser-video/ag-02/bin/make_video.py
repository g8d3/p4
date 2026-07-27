#!/usr/bin/env python3
"""
make_video.py — Pipeline completo para generar videos AI News.

Uso:
  python3 make_video.py output/script.md output/narration.mp3

Requiere servicios corriendo:
  - model_worker.py (Parakeet ASR)
  - Chrome con --remote-debugging-port=9222 (para descargar imágenes)
"""
import json, os, re, sys, subprocess, time, shutil, socket, urllib.request
from pathlib import Path
from difflib import SequenceMatcher

BASE = Path(__file__).parent.parent
OUTPUT = BASE / 'output'
IMGDIR = OUTPUT / 'images' / 'stock'
TMP = Path('/tmp') / 'make-video'
WORKER_SOCKET = '/tmp/transcribe-worker.sock'
CHROME_PORT = 9222

os.makedirs(IMGDIR, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

# ─── 1. VALIDAR DEPENDENCIAS ───────────────────────────────────────
def check_deps():
    for cmd in ['ffmpeg', 'agent-browser', 'curl']:
        if not shutil.which(cmd):
            sys.exit(f"Falta: {cmd}")
    if not os.path.exists(WORKER_SOCKET):
        sys.exit("Worker no corriendo. Iniciá: python3 bin/model_worker.py")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('127.0.0.1', CHROME_PORT))
        s.close()
    except:
        sys.exit("Chrome no corriendo en :9222")
    print("[OK] Dependencias OK", flush=True)

# ─── 2. GENERAR TTS (edge-tts, fallback) ──────────────────────────
def generate_tts(script_path, audio_path):
    if audio_path.exists():
        print(f"[TTS] Usando audio existente: {audio_path.name}", flush=True)
        return
    print("[TTS] Generando con edge-tts...", flush=True)
    txt = re.sub(r'\[.*?\]', '', script_path.read_text())
    txt_path = audio_path.with_suffix('.txt')
    txt_path.write_text(re.sub(r'\s+', ' ', txt).strip())
    subprocess.run(['edge-tts', '--voice', 'en-US-GuyNeural',
        '-f', str(txt_path), '--write-media', str(audio_path)],
        check=True, timeout=300)
    dur = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries',
        'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
        str(audio_path)], capture_output=True, text=True).stdout.strip()
    print(f"  {audio_path.name} ({float(dur):.0f}s)", flush=True)

# ─── 3. ALINEAR SUBTÍTULOS ────────────────────────────────────────
def align_subtitles(audio_path, script_path):
    print("[ALIGN] Transcribiendo y alineando...", flush=True)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(120)
    sock.connect(WORKER_SOCKET)
    sock.sendall(json.dumps({'path': str(audio_path)}).encode())
    sock.shutdown(socket.SHUT_WR)
    data = b''.join(iter(lambda: sock.recv(65536), b''))
    sock.close()
    result = json.loads(data)
    words_raw = result.get('words_raw', [])

    tag_pat = re.compile(r'(\[[A-Za-z\s]+\])')
    sentences = []
    current_tags = []
    for line in script_path.read_text().strip().split('\n'):
        line = line.strip()
        if not line: continue
        line_tags = tag_pat.findall(line)
        if line_tags: current_tags.extend(line_tags)
        for chunk in re.split(r'\[(?:PAUSE|DRAMATIC PAUSE)\]', line):
            clean = tag_pat.sub('', chunk).strip()
            if not clean: continue
            for s in re.split(r'(?<=[.!?])\s+', clean):
                s = s.strip()
                if s: sentences.append({'text': s, 'tags': list(current_tags) if current_tags else []})
        current_tags = []

    probe_words = [w['text'].lower() for w in words_raw]

    def words_from_text(t):
        return re.findall(r"[a-z0-9']+", t.lower())

    srt_segs, manifest_segs, idx = [], [], 0
    for entry in sentences:
        sent_w = words_from_text(entry['text'])
        if not sent_w: continue
        n = len(sent_w)
        best_off = max(range(-5, 6), key=lambda o: (
            SequenceMatcher(None, sent_w, probe_words[max(0, idx+o):max(0, idx+o)+n]).ratio()
            if max(0, idx+o)+n <= len(probe_words) else 0))
        ai = max(0, idx + best_off)
        matched = words_raw[ai:ai+n]
        if not matched: idx += 1; continue
        for cw in [matched[i:i+5] for i in range(0, len(matched), 5)]:
            srt_segs.append({'start': cw[0]['start'], 'end': cw[-1]['end'],
                'text': ' '.join(w['text'] for w in cw)})
        manifest_segs.append({'text': entry['text'], 'tags': entry['tags'],
            'start': matched[0]['start'], 'end': matched[-1]['end']})
        idx = ai + n

    def fmt(s): h=int(s//3600); m=int((s%3600)//60); return f'{h:02d}:{m:02d}:{s%60:06.3f}'.replace('.',',')
    srt_path = audio_path.with_suffix('.srt')
    with open(srt_path, 'w') as f:
        for i, seg in enumerate(srt_segs, 1):
            f.write(f"{i}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{seg['text']}\n\n")
    manifest_path = audio_path.with_suffix('.manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest_segs, f, indent=2)
    print(f"  SRT: {srt_path.name} ({len(srt_segs)} chunks)", flush=True)
    print(f"  Manifest: {manifest_path.name} ({len(manifest_segs)} sentences)", flush=True)
    return srt_path, manifest_path

# ─── 4. GENERAR ASS (subtítulos con highlighting) ──────────────────
def generate_ass(srt_path, manifest_path):
    print("[ASS] Generando subtítulos con highlighting...", flush=True)
    with open(manifest_path) as f:
        segments = json.load(f)
    KEYWORDS = ['openai','gpt','hugging face','waic','shanghai','nubia','navix',
        'gartner','google','deepmind','youtube','flux','gemini','microsoft',
        'mistral','uc riverside','black forest','perimeterx','cloudflare',
        'datadome','chatgpt','sol','chatbot']

    ass_path = srt_path.with_suffix('.ass')
    lines = [
        '[Script Info]', 'Title: AI News Subtitles', 'ScriptType: v4.00+',
        'WrapStyle: 0', 'ScaledBorderAndShadow: yes', '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        'Style: Default,Inter,18,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,60,60,50,1',
        'Style: HL,Inter,18,&H00FFCC00,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,0,2,60,60,50,1',
        '', '[Events]',
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
    ]
    with open(srt_path) as f:
        srt_text = f.read()
    srt_blocks = srt_text.strip().split('\n\n')

    # Segment-level timing mapping
    seg_times = [(s['start'], s['end'], s['text']) for s in segments]

    for block in srt_blocks:
        lines_b = block.strip().split('\n')
        if len(lines_b) < 3: continue
        time_b = lines_b[1]
        m = re.match(r'(\d+:\d+:\d+,\d+) --> (\d+:\d+:\d+,\d+)', time_b)
        if not m: continue
        text = ' '.join(lines_b[2:])
        words = text.split()
        styled = []
        for w in words:
            clean = w.lower().strip('.,!?;\':"')
            if clean in KEYWORDS:
                styled.append(r'{\rHL}' + w + r'{\rDefault}')
            else:
                styled.append(w)
        lines.append(f"Dialogue: 0,{m.group(1)},{m.group(2)},Default,,0,0,0,,{' '.join(styled)}")

    ass_path.write_text('\n'.join(lines))
    print(f"  ASS: {ass_path.name}", flush=True)
    return ass_path

# ─── 5. CORREGIR NÚMEROS EN SRT ───────────────────────────────────
def fix_numbers(srt_path):
    print("[FIX] Corrigiendo números...", flush=True)
    NUM = {'zero':'0','one':'1','two':'2','three':'3','four':'4','five':'5','six':'6',
           'seven':'7','eight':'8','nine':'9','ten':'10','eleven':'11','twelve':'12',
           'thirteen':'13','fourteen':'14','fifteen':'15','sixteen':'16','seventeen':'17',
           'eighteen':'18','nineteen':'19','twenty':'20','thirty':'30','forty':'40',
           'fifty':'50','sixty':'60','seventy':'70','eighty':'80','ninety':'90'}
    text = srt_path.read_text()
    def fix_line(ln):
        for t in ['twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety']:
            for o in ['one','two','three','four','five','six','seven','eight','nine']:
                ln = re.sub(r'\b'+t+r' '+o+r'\b', str(int(NUM[t])+int(NUM[o])), ln)
        for a in list(NUM.keys())[:10]:
            for b in list(NUM.keys())[:10]:
                ln = re.sub(r'\b'+a+r' point '+b+r'\b', NUM[a]+'.'+NUM[b], ln)
        for w, d in list(NUM.items())[:10]:
            ln = re.sub(r'\b'+w+r'\b', d, ln)
        for w, d in list(NUM.items())[10:20]:
            ln = re.sub(r'\b'+w+r'\b', d, ln)
        return ln
    out = []
    for ln in text.split('\n'):
        if ln.strip() and not ln[0].isdigit() and '-->' not in ln and ln.strip():
            ln = fix_line(ln)
        out.append(ln)
    srt_path.write_text('\n'.join(out))
    print(f"  Números corregidos en {srt_path.name}", flush=True)
    return srt_path

# ─── 6. MAPA DE IMÁGENES POR SEGMENTO ─────────────────────────────
SEARCH_TERMS = [
    "globe network animation",         # seg0
    "neural network technology",       # seg1
    "openai office",                   # seg2 ← Ken Burns
    "cyber security shield",           # seg3
    "chatgpt logo",                    # seg4 ← Ken Burns
    "team collaboration",              # seg5 ← Ken Burns
    "network connection technology",   # seg6
    "cyber security containment",      # seg7
    "conference hall",                 # seg8 ← Ken Burns
    "question mark abstract",          # seg9
    "portal light beam",               # seg10
    "smartphone technology",           # seg11 ← Ken Burns
    "brain computer interface",        # seg12
    "business chart financial",        # seg13 ← Ken Burns
    "money counting numbers",          # seg14
    "blocks structure chain",          # seg15
    "magnifying glass search",         # seg16
    "science laboratory",              # seg17 ← Ken Burns
    "video player interface",          # seg18 ← Ken Burns
    "fast motion speed lines",         # seg19
    "abstract colorful art",           # seg20 ← Ken Burns
    "google gemini logo",              # seg21 ← Ken Burns
    "business partnership handshake",  # seg22 ← Ken Burns
    "abstract lines converging",       # seg23
    "expanding rings circles",         # seg24
]

UNSPLASH_TERMS = [
    None, None,
    "openai", None,
    "chatgpt", "team collaboration",
    None, None,
    "conference hall", None, None,
    "smartphone", None,
    "business chart", None, None, None,
    "science lab", "video player", None,
    "abstract art", "google gemini",
    "partnership", None, None,
]

KENBURN_SEGMENTS = {2, 4, 5, 8, 11, 13, 17, 18, 20, 21, 22}

# ─── 7. DESCARGAR IMÁGENES ────────────────────────────────────────
def download_image(term, output_name):
    """Try unsplash first, fallback to google images."""
    out = IMGDIR / output_name
    if out.exists() and out.stat().st_size > 1000:
        return out

    # Try Unsplash directly
    import urllib.parse
    url = f"https://unsplash.com/s/photos/{urllib.parse.quote(term)}"
    subprocess.run(['agent-browser', '--auto-connect', 'open', url],
                  capture_output=True, timeout=20)
    time.sleep(2)
    result = subprocess.run(['agent-browser', '--auto-connect', 'eval',
        'Array.from(document.querySelectorAll("img[src*=\\\"images.unsplash.com\\\"]"))'
        '.filter(i=>i.naturalWidth>300).slice(0,1).map(i=>i.src.split(\"?\")[0]+"?fm=jpg&q=80&w=1920")[0]'],
        capture_output=True, text=True, timeout=15)
    img_url = result.stdout.strip().strip('"')
    if img_url and img_url.startswith('http'):
        urllib.request.urlretrieve(img_url, out)
        if out.stat().st_size > 1000:
            print(f"    Unsplash: {output_name}", flush=True)
            return out

    # Fallback: copy a default abstract image
    print(f"    No image for '{term}', using placeholder", flush=True)
    return None

# ─── 8. GENERAR KEN BURNS ─────────────────────────────────────────
def make_kenburns(image_path, duration, effect, output_path):
    frames = int(duration * 30)
    effects = {
        'slow': "z='1.0+0.005*on'",
        'fast': "z='1.0+0.012*on'",
        'out': "z='1.3-0.005*on'",
        'up': "z='1.1':y='ih/2-(ih/2)*on/100'",
        'left': "z='1.1':x='iw/2-(iw/2)*on/100'",
        'static': "z='1.0'",
    }
    zp = effects.get(effect, effects['slow'])
    filter_str = f"zoompan={zp}:d={frames}:fps=30:s=1080x1920"

    # Handle transparent PNGs
    img_mode = subprocess.run(['python3', '-c',
        f"from PIL import Image;print(Image.open('{image_path}').mode)"],
        capture_output=True, text=True).stdout.strip()
    if 'A' in img_mode:  # has alpha
        jpg = image_path.with_suffix('.tmp.jpg')
        subprocess.run(['ffmpeg', '-y', '-i', str(image_path),
            '-vf', "color=c=white:s=2000x2000[bg];[bg][0]overlay=format=auto",
            '-frames:v', '1', str(jpg)], capture_output=True)
        image_path = jpg

    mp4 = output_path.with_suffix('.mp4')
    subprocess.run(['ffmpeg', '-y', '-i', str(image_path), '-vf', filter_str,
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '22', str(mp4)],
        capture_output=True, timeout=120)
    subprocess.run(['ffmpeg', '-y', '-i', str(mp4), '-c:v', 'libvpx', '-b:v', '2M',
        str(output_path)], capture_output=True, timeout=60)
    if image_path.suffix == '.tmp.jpg':
        image_path.unlink()
    return output_path.exists() and output_path.stat().st_size > 1000

# ─── 9. DESCARGAR VIDEOS DE STOCK ─────────────────────────────────
def download_stock_video(term, duration, output_path):
    """Search Pixabay and download a stock video."""
    if output_path.exists() and output_path.stat().st_size > 1000:
        return True
    import urllib.parse
    url = f"https://pixabay.com/videos/search/{urllib.parse.quote(term)}/"
    subprocess.run(['agent-browser', '--auto-connect', 'open', url],
                  capture_output=True, timeout=20)
    time.sleep(2)
    snap = subprocess.run(['agent-browser', '--auto-connect', 'snapshot', '-i'],
                         capture_output=True, text=True, timeout=15)
    ref = None
    for line in snap.stdout.split('\n'):
        if 'Download' in line and 'ref=' in line:
            m = re.search(r'ref=([a-z0-9]+)', line)
            if m: ref = m.group(1); break
    if not ref: return False
    subprocess.run(['agent-browser', '--auto-connect', 'click', f'@{ref}'],
                  capture_output=True, timeout=20)
    time.sleep(3)
    dl = sorted(Path.home().glob('Downloads/*.mp4'), key=os.path.getmtime, reverse=True)
    if not dl: return False
    subprocess.run(['ffmpeg', '-y', '-i', str(dl[0]), '-t', str(duration),
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
        '-c:v', 'libvpx', '-b:v', '2M', '-c:a', 'libvorbis', str(output_path)],
        capture_output=True, timeout=120)
    return output_path.exists()

# ─── 10. CONSTRUIR VIDEO FINAL ─────────────────────────────────────
def build_video(ass_path, audio_path, output_path, total_dur):
    print("[BUILD] Construyendo video final...", flush=True)
    concat_file = TMP / 'concat.txt'
    with open(concat_file, 'w') as f:
        for i in range(25):
            kb = TMP / f'kb_{i}.webm'
            if kb.exists():
                f.write(f"file {kb}\n")
            else:
                st = TMP / f'stock_{i}.webm'
                if st.exists():
                    f.write(f"file {st}\n")

    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
        '-i', str(audio_path),
        '-vf', f"ass={ass_path}",
        '-map', '0:v', '-map', '1:a', '-shortest',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
        '-c:a', 'aac', '-b:a', '128k',
        str(output_path), '-y'], check=True, timeout=600)
    return True

# ─── MAIN ──────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 3:
        print(f"Uso: {sys.argv[0]} <script.md> <narration.mp3>")
        sys.exit(1)
    script_path = Path(sys.argv[1])
    audio_path = Path(sys.argv[2])
    output_path = OUTPUT / 'FINAL.mp4'

    check_deps()

    # 1. TTS (si no existe el audio)
    generate_tts(script_path, audio_path)

    # 2. Convertir audio a mono si es estéreo
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries',
        'stream=channels', '-of', 'default=noprint_wrappers=1:nokey=1',
        str(audio_path)], capture_output=True, text=True)
    if r.stdout.strip() == '2':
        mono = audio_path.with_suffix('.mono.mp3')
        subprocess.run(['ffmpeg', '-y', '-i', str(audio_path), '-ac', '1', str(mono)],
                      capture_output=True)
        audio_path = mono
        print(f"[AUDIO] Convertido a mono: {audio_path.name}", flush=True)

    # 3. Alinear subtítulos
    srt_path, manifest_path = align_subtitles(audio_path, script_path)

    # 4. Corregir números
    srt_path = fix_numbers(srt_path)

    # 5. Generar ASS
    ass_path = generate_ass(srt_path, manifest_path)

    # 6. Descargar imágenes + Ken Burns
    with open(manifest_path) as f:
        segments = json.load(f)

    print("[IMAGES] Descargando imágenes...", flush=True)
    for idx in KENBURN_SEGMENTS:
        term = UNSPLASH_TERMS[idx]
        if not term: continue
        img = download_image(term, f"seg{idx}.jpg")
        if img and img.exists():
            dur = round(segments[idx]['end'] - segments[idx]['start'] + 0.2, 2)
            effects = ['slow', 'fast', 'out', 'up', 'left', 'static']
            effect = effects[idx % len(effects)]
            out = TMP / f'kb_{idx}.webm'
            ok = make_kenburns(img, dur, effect, out)
            print(f"  [{idx}] Ken Burns ({effect}, {dur}s): {'OK' if ok else 'FAIL'}", flush=True)

    # 7. Descargar videos de stock Pixabay
    print("[STOCK] Descargando videos...", flush=True)
    for i in range(25):
        if i in KENBURN_SEGMENTS: continue
        out = TMP / f'stock_{i}.webm'
        if out.exists() and out.stat().st_size > 1000: continue
        dur = round(segments[i]['end'] - segments[i]['start'] + 0.2, 2)
        print(f"  [{i}] {SEARCH_TERMS[i]} ({dur}s)", flush=True)
        download_stock_video(SEARCH_TERMS[i], dur, out)

    # 8. Construir video final
    total_dur = round(segments[-1]['end'] + 0.3, 2)
    build_video(ass_path, audio_path, output_path, total_dur)

    # 9. Verificar
    info = json.loads(subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_entries', 'format=duration,size', '-show_streams', str(output_path)],
        capture_output=True, text=True).stdout)
    dur = float(info['format']['duration'])
    size = int(info['format']['size'])
    v = [s for s in info['streams'] if s['codec_type']=='video'][0]
    print(f"\n[OK] {output_path.name}")
    print(f"  {dur:.0f}s | {size/1024/1024:.0f}MB | {v['width']}x{v['height']}")

if __name__ == '__main__':
    main()
