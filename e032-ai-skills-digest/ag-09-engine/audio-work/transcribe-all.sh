#!/usr/bin/env bash
set -u
DG=/home/vuos/code/p4/e029-html-video-explainer/bin/dg-transcribe.sh
V=/home/vuos/code/p4/e032-ai-skills-digest/ag-09-engine/videos/dia-1-reto/assets/voice
OUT=/home/vuos/code/p4/e032-ai-skills-digest/ag-09-engine/audio-work/transcripts
LOG=/home/vuos/code/p4/e032-ai-skills-digest/ag-09-engine/audio-work/transcribe.log
> "$LOG"
for n in $(seq -w 1 4); do
  s=$(date +%s)
  "$DG" -q -l es -m nova-3 "$V/${n}.mp3" "$OUT/${n}.json" 2>>"$LOG"
  e=$(date +%s)
  echo "transcribed ${n} in $((e-s))s" >> "$LOG"
done
echo "ALL_DONE" >> "$LOG"
