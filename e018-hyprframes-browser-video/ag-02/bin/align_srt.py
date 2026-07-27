#!/usr/bin/env python3
"""Align script sentences with Parakeet word timestamps → clean SRT with short segments."""
import re, json, sys, os, socket
from difflib import SequenceMatcher

WORKER_SOCKET = '/tmp/transcribe-worker.sock'

def call_worker(audio_path):
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

def clean_script(text):
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'[\u2014\u2013]', ' ', text)
    text = re.sub(r'\u2026', '...', text)
    return re.sub(r'\s+', ' ', text).strip()

def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

def words_from_text(text):
    return re.findall(r"[a-z0-9']+", text.lower())

def fmt_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')

def chunk_words(word_list, max_words=5):
    """Split word list into chunks of max_words."""
    return [word_list[i:i+max_words] for i in range(0, len(word_list), max_words)]

if __name__ == '__main__':
    audio_path = sys.argv[1] if len(sys.argv) > 1 else \
        '/home/vuos/code/p4/e018-hyprframes-browser-video/ag-02/output/ai-news.mp3'
    base = os.path.dirname(audio_path)
    script_path = os.path.join(base, 'script.md')

    # 1. Read script
    with open(script_path) as f:
        raw = f.read()

    tag_pattern = re.compile(r'(\[[A-Za-z\s]+\])')
    tagged_sentences = []
    current_tags = []
    for line in raw.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        line_tags = tag_pattern.findall(line)
        if line_tags:
            current_tags.extend(line_tags)
        chunks = re.split(r'\[(?:PAUSE|DRAMATIC PAUSE)\]', line)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            clean_text = tag_pattern.sub('', chunk).strip()
            if not clean_text:
                continue
            sents = split_sentences(clean_text)
            for s in sents:
                tagged_sentences.append({'text': s, 'tags': list(current_tags) if current_tags else []})
        current_tags = []

    # 2. Transcribe via worker
    print(f'Transcribing {os.path.basename(audio_path)}...', flush=True)
    result = call_worker(audio_path)
    words_raw = result.get('words_raw', [])
    if not words_raw:
        print('ERROR: no word timestamps', flush=True)
        sys.exit(1)

    probe_words = [w['text'].lower() for w in words_raw]

    # 3. For each sentence, get word timestamps, then chunk into short groups
    srt_segments = []
    manifest_segments = []
    idx = 0

    for si, entry in enumerate(tagged_sentences):
        sent = entry['text']
        tags = entry['tags']
        sent_words = words_from_text(sent)
        n = len(sent_words)

        if n == 0:
            continue

        # Find alignment via fuzzy match
        best_ratio = 0
        best_offset = 0
        for offset in range(-5, 6):
            start = max(0, idx + offset)
            end = start + n
            if end > len(probe_words):
                continue
            ratio = SequenceMatcher(None, sent_words, probe_words[start:end]).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_offset = offset

        aligned_idx = max(0, idx + best_offset)

        # Get the matching words from probe (with timestamps)
        matched = words_raw[aligned_idx:aligned_idx + n]
        if not matched:
            idx += 1
            continue

        # Chunk the matched words into short groups
        chunks = chunk_words(matched, 5)
        for chunk in chunks:
            srt_segments.append({
                'start': chunk[0]['start'],
                'end': chunk[-1]['end'],
                'text': ' '.join(w['text'] for w in chunk)
            })

        manifest_segments.append({
            'text': sent,
            'tags': tags,
            'start': matched[0]['start'],
            'end': matched[-1]['end']
        })

        idx = aligned_idx + n

    # 4. Write SRT
    srt_path = os.path.join(base, 'ai-news.srt')
    with open(srt_path, 'w') as f:
        for i, seg in enumerate(srt_segments, 1):
            f.write(f"{i}\n{fmt_time(seg['start'])} --> {fmt_time(seg['end'])}\n{seg['text']}\n\n")

    # 5. Write manifest
    manifest_path = os.path.join(base, 'ai-news-manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest_segments, f, indent=2)

    print(f'SRT: {srt_path} ({len(srt_segments)} subtitle chunks)', flush=True)
    print(f'Manifest: {manifest_path} ({len(manifest_segments)} sentences)', flush=True)
    for seg in srt_segments[:10]:
        print(f"  {fmt_time(seg['start'])} → {fmt_time(seg['end'])}  {seg['text']}", flush=True)
    if len(srt_segments) > 10:
        print(f'  ... and {len(srt_segments)-10} more', flush=True)
