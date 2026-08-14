#!/usr/bin/env python3
"""Cloud transcription via Deepgram nova-3 (word timestamps).

Replaces the broken local Parakeet worker. Same output shape as the local
transcribe server: writes <audio>.txt, <audio>.srt, <audio>.words.json and
prints JSON {text, srt, words_raw}.

Usage: transcribe_cloud.py <audio.mp3|wav>
"""
import json, os, sys, urllib.request

API = "https://api.deepgram.com/v1/listen"
KEY = os.environ.get("DEEPGRAM_API_KEY")
PARAMS = ("?model=nova-3&smart_format=true&punctuate=true"
          "&timestamps=true&language=en")
CTYPE = {"mp3": "audio/mpeg", "wav": "audio/wav", "mp4": "audio/mp4"}


def main(audio):
    if not KEY:
        sys.exit("DEEPGRAM_API_KEY not set")
    ext = os.path.splitext(audio)[1].lstrip(".").lower()
    ctype = CTYPE.get(ext, "audio/mpeg")
    with open(audio, "rb") as f:
        data = f.read()
    req = urllib.request.Request(API + PARAMS, data=data, method="POST",
                                 headers={"Authorization": f"Token {KEY}",
                                          "Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    alt = res["results"]["channels"][0]["alternatives"][0]
    text = (alt.get("transcript") or "").strip()
    words_raw = []
    for w in alt.get("words") or []:
        word = w.get("punctuated_word") or w.get("word") or ""
        words_raw.append({"start": round(w["start"], 3),
                          "end": round(w["end"], 3),
                          "text": word})

    def srt_ts(t):
        ms = int(round(t * 1000))
        h, rem = divmod(ms, 3600000)
        m, rem = divmod(rem, 60000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    srt_lines = []
    for i, w in enumerate(words_raw, 1):
        srt_lines.append(f"{i}\n{srt_ts(w['start'])} --> {srt_ts(w['end'])}\n{w['text']}\n")
    srt = "\n".join(srt_lines)

    base = os.path.splitext(audio)[0]
    with open(base + ".txt", "w") as f:
        f.write(text + "\n")
    with open(base + ".srt", "w") as f:
        f.write(srt)
    with open(base + ".words.json", "w") as f:
        json.dump(words_raw, f)
    print(json.dumps({"text": text, "srt": srt, "words_raw": words_raw}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: transcribe_cloud.py <audio>")
    main(sys.argv[1])
