#!/usr/bin/env python3
"""Generate TikTok-style subtitle SRT — dynamic timing from recorded events."""
import json, os

BASE = "/home/vuos/code/p4/e010-more-videos/ag-03"
OUT_SRT = f"{BASE}/assets/subtitles.srt"
RECORD_TIMING = f"{BASE}/assets/record_timing.json"
TIMING_EVENTS = f"{BASE}/assets/timing.events"

def sec_to_srt(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60); ms = int((t % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# Read timing
with open(RECORD_TIMING) as f:
    rt = json.load(f)
rec_start = rt["rec_start"]; offset = rt["offset_sec"]

events = {}
with open(TIMING_EVENTS) as f:
    for line in f:
        parts = line.strip().split(" ", 1)
        events[parts[1]] = float(parts[0]) - rec_start - offset

# Build subtitles from events
subs = []
t = events["intro_start"]
tts_play = events["tts_play_start"]
tts_play_end = events["tts_play_end"]
asr_exec = events["asr_exec_start"]
asr_done = events["asr_exec_done"]
outro = events["outro_start"]

# Intro section
subs.append(("Xiaomi MIMO", 0.5, min(3.0, t + 3)))
subs.append(("TTS + ASR Demo", min(3.0, t + 3), t + 5.5))
subs.append(("Text to Speech", t + 5.5, events["tts_cmd_done"] - 2))
subs.append(("Convert text to AI voice", events["tts_cmd_done"] - 2, events["tts_cmd_done"] + 1))
subs.append(("mimo-v2.5-tts", events["tts_cmd_done"] + 1, events["tts_exec_start"] + 0.5))
subs.append(("Calling Xiaomi API...", events["tts_exec_start"] + 0.5, events["tts_exec_start"] + 3))
subs.append(("Generating audio...", events["tts_exec_start"] + 3, events["tts_exec_done"] - 0.5))
subs.append(("Listen to the AI voice", events["tts_exec_done"] - 0.5, tts_play))

# TTS playback — subtitles continue (narration silent)
mid1 = tts_play + (tts_play_end - tts_play) / 3
mid2 = tts_play + 2 * (tts_play_end - tts_play) / 3
subs.append(("\u25b6 Playing TTS Audio", tts_play, mid1))
subs.append(("[AI Voice]", mid1, mid2))
subs.append(("\u25b6 Playing TTS Audio", mid2, tts_play_end))

# Post-playback + ASR section
subs.append(("Now: Speech to Text", tts_play_end, tts_play_end + 3))
subs.append(("Transcribe audio -> text", tts_play_end + 3, asr_exec - 1))
subs.append(("mimo-v2.5-asr", asr_exec - 1, asr_exec + 1))
subs.append(("Processing audio...", asr_exec + 1, asr_done))

# Result + outro
subs.append(("Transcription result", asr_done, outro))
subs.append(("Complete voice pipeline!", outro, outro + 3.5))
subs.append(("Thanks for watching", outro + 3.5, outro + 6.5))

# Write SRT
with open(OUT_SRT, "w") as f:
    for i, (text, start, end) in enumerate(subs, 1):
        start = max(0, start)
        end = max(start + 0.5, end)
        f.write(f"{i}\n{sec_to_srt(start)} --> {sec_to_srt(end)}\n{text}\n\n")

# Verify no gaps >3s
for i in range(len(subs) - 1):
    gap = subs[i+1][1] - subs[i][2]
    if gap > 3.0:
        print(f"  WARNING: {gap:.1f}s gap after '{subs[i][0]}'")

total = subs[-1][2] - subs[0][1]
print(f"Subtitles: {len(subs)} segments, {total:.1f}s covered (0-{subs[-1][2]:.1f}s)")
