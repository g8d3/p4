#!/bin/bash
set -e

ASSETS="/home/vuos/code/p4/e010-more-videos/ag-03/assets"
NARR="$ASSETS/narration"
TTS_AUDIO="$ASSETS/tts_demo.wav"
OUT="$ASSETS/audio_mix.aac"

# Audio timeline (ms):
#  01_intro:       0ms
#  02_tts_cmd:     6500ms
#  03_tts_result:  17000ms  ("Escuchen...")
#  tts_demo.wav:   20500ms  (actual TTS audio playback)
#  04_tts_comment: 28500ms
#  05_asr_cmd:     35000ms
#  06_asr_result:  40500ms
#  07_outro:       47500ms

timeout 30 ffmpeg -y \
  -i "$NARR/01_intro.mp3" \
  -i "$NARR/02_tts_cmd.mp3" \
  -i "$NARR/03_tts_result.mp3" \
  -i "$TTS_AUDIO" \
  -i "$NARR/04_tts_comment.mp3" \
  -i "$NARR/05_asr_cmd.mp3" \
  -i "$NARR/06_asr_result.mp3" \
  -i "$NARR/07_outro.mp3" \
  -filter_complex "\
[0:a]adelay=0|0[a0];\
[1:a]adelay=6500|6500[a1];\
[2:a]adelay=17000|17000[a2];\
[3:a]adelay=20500|20500,volume=1.8[a3];\
[4:a]adelay=28500|28500[a4];\
[5:a]adelay=35000|35000[a5];\
[6:a]adelay=40500|40500[a6];\
[7:a]adelay=47500|47500[a7];\
[a0][a1][a2][a3][a4][a5][a6][a7]amix=inputs=8:duration=longest:normalize=0[aout]" \
  -map "[aout]" -ac 2 -ar 44100 -c:a aac -b:a 128k \
  "$OUT" 2>&1

echo "Audio mix saved: $OUT ($(stat -c%s "$OUT") bytes)"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
