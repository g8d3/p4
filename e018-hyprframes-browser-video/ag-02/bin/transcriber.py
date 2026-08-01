#!/usr/bin/env python3
"""Persistent transcriber — model stays in memory, logs timing."""
import nemo.collections.asr as nemo_asr
import time, csv, os, sys, json, subprocess, math
from pathlib import Path
from statistics import mean, stdev

LOG = Path(__file__).parent.parent / 'output' / 'transcribe_log.csv'
MODEL_PATH = os.environ.get(
    'PARAKEET_MODEL',
    str(Path.home() / 'models' / 'parakeet-ctc-0.6b.nemo')
)

# Track load time per session
LOAD_SEC = None

MODEL = None

def ensure_model():
    global LOAD_SEC, MODEL
    if MODEL is not None:
        return MODEL
    print('Loading model...', flush=True)
    t0 = time.time()
    MODEL = nemo_asr.models.EncDecCTCModelBPE.restore_from(MODEL_PATH)
    LOAD_SEC = time.time() - t0
    # Set faster decoding
    MODEL.cfg.decoding.strategy = 'greedy_batch'
    MODEL.change_decoding_strategy(MODEL.cfg.decoding)
    print(f'Model loaded in {LOAD_SEC:.1f}s', flush=True)
    return MODEL

def fmt_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')

def segment_words(word_list):
    """Split words into segments using statistical gap analysis."""
    if len(word_list) < 2:
        return [{'start': word_list[0]['start'], 'end': word_list[0]['end'], 'text': word_list[0]['text']}]

    gaps = []
    for i in range(len(word_list) - 1):
        gaps.append(word_list[i+1]['start'] - word_list[i]['end'])

    avg_gap = mean(gaps)
    std_gap = stdev(gaps) if len(gaps) > 1 else 0.1
    threshold = avg_gap + 1.5 * std_gap

    segments = []
    current = []
    current_start = None
    dur = 0
    for i, w in enumerate(word_list):
        if current_start is None:
            current_start = w['start']
        current.append(w['text'])
        dur = w['end'] - current_start

        gap_to_next = word_list[i+1]['start'] - w['end'] if i < len(word_list) - 1 else 0
        is_significant_pause = gap_to_next > threshold and len(current) >= 3
        is_long = dur > 5.0
        is_end = i == len(word_list) - 1

        if is_significant_pause or is_long or is_end:
            segments.append({'start': current_start, 'end': w['end'], 'text': ' '.join(current)})
            current = []
            current_start = None
            dur = 0

    return segments

def transcribe(audio_path):
    global LOAD_SEC
    model = ensure_model()
    audio_path = Path(audio_path)
    if not audio_path.exists():
        print(f'File not found: {audio_path}', flush=True)
        return
    base = audio_path.with_suffix('')
    srt_path = base.with_suffix('.srt')
    txt_path = base.with_suffix('.txt')

    # Get audio duration
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_entries', 'format=duration', str(audio_path)], capture_output=True, text=True)
    audio_sec = float(json.loads(r.stdout)['format']['duration'])

    print(f'Transcribing {audio_path.name} ({audio_sec:.0f}s audio)...', flush=True)
    t0 = time.time()
    result = model.transcribe([str(audio_path)], return_hypotheses=True, timestamps=True)[0]
    transcribe_sec = time.time() - t0

    words_raw = result.timestamp['word']
    text = result.text

    # Save TXT
    with open(txt_path, 'w') as f:
        f.write(text + '\n')

    word_list = []
    for w in words_raw:
        start = int(w['start_offset']) * 0.08
        end = int(w['end_offset']) * 0.08
        word_list.append({'text': w['word'], 'start': start, 'end': end})

    segments = segment_words(word_list)

    # Save SRT
    with open(srt_path, 'w') as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n{fmt_time(seg['start'])} --> {fmt_time(seg['end'])}\n{seg['text']}\n\n")

    # Log — load_sec only for first transcription in session
    load_for_log = round(LOAD_SEC, 1) if LOAD_SEC else 0
    LOAD_SEC = 0  # subsequent calls don't reload

    LOG.parent.mkdir(parents=True, exist_ok=True)
    if not LOG.exists():
        with open(LOG, 'w', newline='') as f:
            csv.writer(f).writerow(['file', 'audio_sec', 'load_sec', 'transcribe_sec', 'total_sec', 'words', 'segments'])

    with open(LOG, 'a', newline='') as f:
        csv.writer(f).writerow([str(audio_path), round(audio_sec, 1), load_for_log,
                                round(transcribe_sec, 1), round(transcribe_sec + load_for_log, 1),
                                len(words_raw), len(segments)])

    speed = f'{audio_sec/transcribe_sec:.1f}x' if transcribe_sec > 0 else '?'
    gap_info = f'gaps>avg+{1.5}std'
    print(f'  TXT: {txt_path}', flush=True)
    print(f'  SRT: {srt_path} ({len(segments)} segments, split on {gap_info})', flush=True)
    print(f'  Time: load={load_for_log}s + transcribe={transcribe_sec}s ({speed} realtime)', flush=True)

def show_log(limit=5):
    if not LOG.exists():
        print('No log yet', flush=True)
        return
    with open(LOG) as f:
        lines = f.readlines()
    if len(lines) <= 1:
        print('No entries yet', flush=True)
        return
    print(f'\nLast {min(limit, len(lines)-1)} transcriptions:')
    print(f'  {"FILE":<30} {"AUDIO":>7} {"LOAD":>6} {"TRANS":>7} {"RATIO":>7} {"WORDS":>6} {"SEG":>4}')
    for line in lines[-limit:]:
        row = line.strip().split(',')
        if len(row) >= 7 and row[0] != 'file':
            fname = Path(row[0]).name
            t = float(row[3]) if row[3] else 0
            a = float(row[1]) if row[1] else 0
            l = float(row[2]) if row[2] else 0
            ratio = t / a if a > 0 else 0
            print(f'  {fname:<30} {a:>7}s {l:>6}s {t:>7}s {ratio:>6.2f}x {row[5]:>6} {row[6]:>4}')

if __name__ == '__main__':
    args = sys.argv[1:]
    if args:
        for a in args:
            transcribe(a)
    else:
        print('Interactive mode — enter file paths (or "log" for history, "q" to quit)')
        while True:
            try:
                inp = input('> ').strip()
            except EOFError:
                break
            if not inp:
                continue
            if inp == 'q':
                break
            if inp == 'log':
                show_log()
                continue
            transcribe(inp)
