#!/usr/bin/env python3
"""Model worker — loads parakeet once, serves requests via Unix socket."""
import nemo.collections.asr as nemo_asr
import time, json, os, sys, socket, struct, signal
from pathlib import Path
from statistics import mean, stdev

MODEL_PATH = os.environ.get(
    'PARAKEET_MODEL',
    str(Path.home() / 'models' / 'parakeet-ctc-0.6b.nemo')
)
SOCKET_PATH = '/tmp/transcribe-worker.sock'

def fmt_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')

def segment_words(word_list):
    if len(word_list) < 2:
        return [{'start': word_list[0]['start'], 'end': word_list[0]['end'], 'text': word_list[0]['text']}]
    gaps = [word_list[i+1]['start'] - word_list[i]['end'] for i in range(len(word_list) - 1)]
    avg = mean(gaps)
    std = stdev(gaps) if len(gaps) > 1 else 0.1
    threshold = avg + 1.5 * std
    segs, cur, cur_start = [], [], None
    for i, w in enumerate(word_list):
        if cur_start is None: cur_start = w['start']
        cur.append(w['text'])
        dur = w['end'] - cur_start
        gap = word_list[i+1]['start'] - w['end'] if i < len(word_list) - 1 else 0
        if (gap > threshold and len(cur) >= 3) or dur > 5.0 or i == len(word_list) - 1:
            segs.append({'start': cur_start, 'end': w['end'], 'text': ' '.join(cur)})
            cur, cur_start = [], None
    return segs

def process(audio_path):
    t0 = time.time()
    result = model.transcribe([str(audio_path)], return_hypotheses=True, timestamps=True)[0]
    t1 = time.time()
    words, text = result.timestamp['word'], result.text
    wl = [{'text': w['word'], 'start': int(w['start_offset']) * 0.08, 'end': int(w['end_offset']) * 0.08} for w in words]
    segs = segment_words(wl)
    srt_lines = [f"{i}\n{fmt_time(s['start'])} --> {fmt_time(s['end'])}\n{s['text']}\n" for i, s in enumerate(segs, 1)]
    return {'text': text, 'srt': '\n'.join(srt_lines), 'transcribe_sec': round(t1 - t0, 2),
            'word_count': len(wl), 'segments': len(segs), 'words_raw': wl}

# Load model
print('Worker loading model...', flush=True)
t0 = time.time()
model = nemo_asr.models.EncDecCTCModelBPE.restore_from(MODEL_PATH)
model.cfg.decoding.strategy = 'greedy_batch'
model.change_decoding_strategy(model.cfg.decoding)
print(f'Worker model loaded in {time.time()-t0:.1f}s', flush=True)

# Clean up old socket
if os.path.exists(SOCKET_PATH):
    os.unlink(SOCKET_PATH)

server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(SOCKET_PATH)
server.listen(5)
os.chmod(SOCKET_PATH, 0o777)
print(f'Worker listening on {SOCKET_PATH}', flush=True)

signal.signal(signal.SIGTERM, lambda *a: exit(0))

def handle(conn):
    data = b''
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            break
        data += chunk
        try:
            req = json.loads(data)
            break
        except json.JSONDecodeError:
            continue
    path = req.get('path', '')
    if not os.path.exists(path):
        conn.sendall(json.dumps({'error': f'File not found: {path}'}).encode())
    else:
        result = process(path)
        conn.sendall(json.dumps(result).encode())
    conn.close()

while True:
    conn, _ = server.accept()
    handle(conn)
