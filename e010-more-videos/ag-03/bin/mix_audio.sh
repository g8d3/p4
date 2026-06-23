#!/bin/bash
set -e

ASSETS="/home/vuos/code/p4/e010-more-videos/ag-03/assets"
NARR="$ASSETS/narration"
TTS_AUDIO="$ASSETS/tts_xiaomi.wav"
OUT="$ASSETS/audio_mix.aac"

# Scene timeline (ms):
#  01_intro:       0ms       (6.5s)
#  02_tts_cmd:     6500ms    (11s)
#  03_tts_result:  17500ms   (8s)  "Escuchen..."
#  04_tts_comment: 17500ms   (8s)  overlapping
#  05_tts_play:    25500ms   (8s)  actual TTS audio playback
#  tts_xiaomi.wav: 26000ms   (8s)
#  06_asr_cmd:     33500ms   (5.5s)
#  07_asr_result:  39000ms   (7s)
#  08_outro:       46000ms   (6s)

timeout 30 ffmpeg -y \
  -i "$NARR/01_intro.mp3" \
  -i "$NARR/02_tts_cmd.mp3" \
  -i "$NARR/03_tts_result.mp3" \
  -i "$NARR/04_tts_comment.mp3" \
  -i "$NARR/05_tts_play.mp3" \
  -i "$TTS_AUDIO" \
  -i "$NARR/06_asr_cmd.mp3" \
  -i "$NARR/07_asr_result.mp3" \
  -i "$NARR/08_outro.mp3" \
  -filter_complex "\
[0:a]adelay=0|0[a0];\
[1:a]adelay=6500|6500[a1];\
[2:a]adelay=17500|17500[a2];\
[3:a]adelay=17500|17500[a3];\
[4:a]adelay=25500|25500[a4];\
[5:a]adelay=26000|26000,volume=1.5[a5];\
[6:a]adelay=33500|33500[a6];\
[7:a]adelay=39000|39000[a7];\
[8:a]adelay=46000|46000[a8];\
[a0][a1][a2][a3][a4][a5][a6][a7][a8]amix=inputs=9:duration=longest:normalize=0[aout]" \
  -map "[aout]" -ac 2 -ar 44100 -c:a aac -b:a 128k \
  "$OUT" 2>&1

echo "Audio mix saved: $OUT ($(stat -c%s "$OUT") bytes)"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
