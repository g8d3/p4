#!/usr/bin/env python3
"""Generate narration segments and mix audio track.
Narration uses es-CO-SalomeNeural (edge-tts).
TTS audio from Xiaomi API is inserted at the playback moment.
Silence is maintained during TTS playback (narration pauses).
"""
import asyncio, edge_tts, json, os, subprocess, sys

BASE = "/home/vuos/code/p4/e010-more-videos/ag-03"
NARR_DIR = f"{BASE}/assets/narration"
TTS_AUDIO = f"{BASE}/assets/tts_demo_final.wav"
OUT_AUDIO = f"{BASE}/assets/audio_final.wav"
TIMING_EVENTS = f"{BASE}/assets/timing.events"
RECORD_TIMING = f"{BASE}/assets/record_timing.json"
VOICE = "es-CO-SalomeNeural"
TRIM = 2.0  # seconds trimmed from start of video

os.makedirs(NARR_DIR, exist_ok=True)

# Read timing
with open(RECORD_TIMING) as f:
    rt = json.load(f)
rec_start = rt["rec_start"]
offset = rt["offset_sec"]

events = {}
with open(TIMING_EVENTS) as f:
    for line in f:
        parts = line.strip().split(" ", 1)
        events[parts[1]] = float(parts[0]) - rec_start - offset

# Narration segments: (id, text, start_time_func)
# Times are relative to trimmed video (0 = start of trimmed video)
SEGMENTS = [
    ("01_intro", "Demostracion de la API de Xiaomi MIMO. Sintesis de voz y reconocimiento de audio.", 0.0),
    ("02_tts_explain", "Usamos el modelo de sintesis de voz para convertir texto en audio. La inteligencia artificial genera una voz natural en espanol.", 5.0),
    ("03_api_process", "La API procesa nuestra solicitud. El modelo mimo v2.5 genera audio desde el texto en segundos.", events.get("tts_exec_start", 14.5)),
    ("04_pre_play", "Escuchen el audio generado por inteligencia artificial.", events.get("tts_exec_done", 21.5)),
    # SILENCE during TTS playback (events["tts_play_start"] to events["tts_play_end"])
    ("05_post_play", "Excelente. Ahora usamos reconocimiento de voz para transcribir el audio.", events.get("tts_play_end", 36.7) + 0.5),
    ("06_asr_process", "La API esta procesando el audio. Reconociendo las palabras con inteligencia artificial.", events.get("asr_exec_start", 43.5)),
    ("07_asr_result", "La API reconoce las palabras y devuelve la transcripcion.", events.get("asr_exec_done", 48.3)),
    ("08_outro", "Dos APIs que juntas crean un sistema de voz completo. Gracias por ver.", events.get("outro_start", 51.3)),
]

async def gen_narration():
    print(f"Generating {len(SEGMENTS)} narration segments with {VOICE}...")
    for seg_id, text, _ in SEGMENTS:
        out = os.path.join(NARR_DIR, f"{seg_id}.mp3")
        comm = edge_tts.Communicate(text, VOICE, rate="+8%")
        await comm.save(out)
        dur = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", out]).decode().strip()
        print(f"  {seg_id}.mp3 ({dur}s)")
    print("Narration generation complete.")

def mix_audio():
    print("\nMixing audio track...")

    # Get TTS audio duration
    tts_dur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", TTS_AUDIO]).decode().strip())

    # TTS playback start time in trimmed video
    tts_play_start = events.get("tts_play_start", 23.6)

    # Build ffmpeg command with all inputs
    inputs = []
    for seg_id, _, _ in SEGMENTS:
        inputs += ["-i", os.path.join(NARR_DIR, f"{seg_id}.mp3")]
    inputs += ["-i", TTS_AUDIO]

    # Build filter: delay each segment to its start time, mix together
    # TTS audio gets a delay and volume boost
    filters = []
    mix_inputs = []

    for i, (seg_id, _, start_time) in enumerate(SEGMENTS):
        delay_ms = int(start_time * 1000)
        filters.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
        mix_inputs.append(f"[a{i}]")

    # TTS audio
    tts_idx = len(SEGMENTS)
    tts_delay_ms = int(tts_play_start * 1000)
    filters.append(f"[{tts_idx}:a]adelay={tts_delay_ms}|{tts_delay_ms},volume=2.0[a{tts_idx}]")
    mix_inputs.append(f"[a{tts_idx}]")

    n_inputs = tts_idx + 1
    mix_str = "".join(mix_inputs)
    filters.append(
        f"{mix_str}amix=inputs={n_inputs}:duration=longest:normalize=0[aout]"
    )

    filter_complex = ";".join(filters)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-ac", "2", "-ar", "44100",
        "-c:a", "pcm_s16le",
        "-t", "58",
        OUT_AUDIO,
    ]

    print(f"Running ffmpeg mix ({n_inputs} audio sources)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: ffmpeg failed:\n{result.stderr[-500:]}")
        sys.exit(1)

    dur = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", OUT_AUDIO]).decode().strip()
    size = os.path.getsize(OUT_AUDIO)
    print(f"Audio mix saved: {OUT_AUDIO} ({size} bytes, {dur}s)")

    # Save subtitle timing data for subtitle generation
    sub_data = []
    for seg_id, text, start_time in SEGMENTS:
        mp3 = os.path.join(NARR_DIR, f"{seg_id}.mp3")
        dur = float(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", mp3]).decode().strip())
        sub_data.append({"id": seg_id, "text": text, "start": start_time, "duration": dur})

    # Add TTS subtitle
    sub_data.append({
        "id": "tts_audio",
        "text": "[TTS Audio Playing]",
        "start": tts_play_start,
        "duration": tts_dur,
    })

    with open(f"{BASE}/assets/subtitle_timing.json", "w") as f:
        json.dump(sub_data, f, indent=2, ensure_ascii=False)
    print("Subtitle timing saved.")

async def main():
    await gen_narration()
    mix_audio()

if __name__ == "__main__":
    asyncio.run(main())
