#!/usr/bin/env bash
set -u
KIE=/home/vuos/code/p4/e019-kie-image-api/ag-01/bin/kie-tts.sh
VOICE=Alnilam
OUT=/home/vuos/code/p4/e032-ai-skills-digest/ag-10-engine/videos/dia-2-voz/assets/voice
SC=/home/vuos/code/p4/e032-ai-skills-digest/ag-10-engine/videos/dia-2-voz/audio-work/scenes.txt
LOG=/home/vuos/code/p4/e032-ai-skills-digest/ag-10-engine/videos/dia-2-voz/audio-work/tts.log
> "$LOG"
START=$(date +%s)
while IFS='|' read -r n text; do
  [ -z "$n" ] && continue
  s=$(date +%s)
  out="$OUT/${n}.mp3"
  mp3=$("$KIE" --voice "$VOICE" --quiet --tag "s${n}" "$text" 2>>"$LOG")
  mv -f "$mp3" "$out" 2>/dev/null
  d=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$out" 2>/dev/null)
  e=$(date +%s)
  echo "scene $n ok dur=$d elapsed=$((e-s))s" >> "$LOG"
  sleep 2
done < "$SC"
echo "ALL_DONE total=$(( $(date +%s) - START ))s" >> "$LOG"
