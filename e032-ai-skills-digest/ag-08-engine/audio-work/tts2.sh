#!/usr/bin/env bash
# Regenerate all 13 scene narrations with explicit line indexing (robust naming).
set -u
KIE=/home/vuos/code/p4/e019-kie-image-api/ag-01/bin/kie-tts.sh
VOICE=Alnilam
OUT=/home/vuos/code/p4/e032-ai-skills-digest/ag-08-engine/videos/reto-7-dias-primer-video/assets/voice
SC=/home/vuos/code/p4/e032-ai-skills-digest/ag-08-engine/audio-work/scenes.txt
LOG=/home/vuos/code/p4/e032-ai-skills-digest/ag-08-engine/audio-work/tts2.log
> "$LOG"
i=0
while IFS='|' read -r _ text; do
  i=$((i+1))
  s=$(date +%s)
  out="$OUT/$(printf '%02d' "$i").mp3"
  mp3=$("$KIE" --voice "$VOICE" --quiet --tag "s$i" "$text" 2>>"$LOG")
  mv -f "$mp3" "$out" 2>>"$LOG"
  d=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$out" 2>/dev/null)
  e=$(date +%s)
  echo "scene $i -> $(basename "$out") dur=$d elapsed=$((e-s))s" >> "$LOG"
done < "$SC"
echo "ALL_DONE n=$i" >> "$LOG"
