#!/usr/bin/env bash
set -e

OUTPUT_DIR="/home/vuos/code/p4/e018-hyprframes-browser-video/ag-02/output"
AUDIO="$OUTPUT_DIR/ai-news.mp3"
MANIFEST="$OUTPUT_DIR/ai-news-manifest.json"
SCRIPT="$OUTPUT_DIR/script.md"
SRT="$OUTPUT_DIR/ai-news.srt"
TMPDIR="/tmp/ai-news-build"
mkdir -p "$TMPDIR"

CHROME_PID=$(pgrep -f "remote-debugging-port=9222" | head -1 || true)

cleanup() {
  echo "Cleaning up..."
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo "=== BUILD AI NEWS VIDEO ==="

# Step 1: Download videos from Pixabay for each segment
echo ""
echo "--- Step 1: Download videos ---"

# Visual search terms for each segment (from visual_suggestions.md)
SEARCH_TERMS=(
  "globe network animation"
  "neural network technology"
  "cyber security shield"
  "security guardrails protection"
  "artificial intelligence escape"
  "network connection technology"
  "cyber security containment"
  "debate controversy balance"
  "stage spotlights event"
  "question mark abstract"
  "portal light beam opening"
  "smartphone technology"
  "brain computer interface"
  "bar chart graph business"
  "money counting numbers"
  "blocks structure chain"
  "magnifying glass search"
  "scanning forensic technology"
  "data stream matrix code"
  "fast motion speed lines"
  "colorful abstract art"
  "light flash burst"
  "merging particles connection"
  "abstract lines converging"
  "expanding rings circles"
)

# ONLY process first 3 for now (testing). Remove this line for full build.
SEARCH_TERMS=("${SEARCH_TERMS[@]:0:3}")

get_srt_segment() {
  python3 -c "
import json
with open('$MANIFEST') as f:
    segs = json.load(f)
print(segs[$1]['start'], segs[$1]['end'])
"
}

echo "Found ${#SEARCH_TERMS[@]} segments to process"

for i in "${!SEARCH_TERMS[@]}"; do
  TERM="${SEARCH_TERMS[$i]}"
  SEG_FILE="$TMPDIR/seg_$i.webm"

  if [ -f "$SEG_FILE" ] && [ -s "$SEG_FILE" ]; then
    echo "  [$((i+1))] Using cached: $SEG_FILE"
    continue
  fi

  echo "  [$((i+1))] Searching: $TERM"

  # Open Pixabay search
  agent-browser --auto-connect open "https://pixabay.com/videos/search/$(echo "$TERM" | sed 's/ /%20/g')/" >/dev/null 2>&1
  sleep 2

  # Find download button ref
  DOWNLOAD_REF=$(agent-browser --auto-connect snapshot -i 2>/dev/null | grep -m1 "Download" | grep -oP "ref=\K[a-z0-9]+")
  if [ -z "$DOWNLOAD_REF" ]; then
    echo "    No download button found, skipping"
    continue
  fi

  # Click download
  agent-browser --auto-connect click "@$DOWNLOAD_REF" >/dev/null 2>&1
  sleep 2

  # Find the newest mp3/mp4 in Downloads
  LATEST=$(ls -t ~/Downloads/*.mp4 2>/dev/null | head -1)
  if [ -z "$LATEST" ] || [ ! -f "$LATEST" ]; then
    echo "    No file downloaded"
    continue
  fi

  # Get segment duration from manifest (+ 0.2s padding)
  read SEG_START SEG_END <<< $(get_srt_segment $i)
  SEG_DUR=$(python3 -c "print(round($SEG_END - $SEG_START + 0.2, 2))")
  echo "    Duration needed: ${SEG_DUR}s"

  # Convert to WebM with correct dimensions
  ffmpeg -y -i "$LATEST" -t "$SEG_DUR" \
    -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" \
    -c:v libvpx -b:v 2M -c:a libvorbis "$SEG_FILE" 2>/dev/null

  echo "    Saved: $SEG_FILE"
done

# Step 2: Create concat list
echo ""
echo "--- Step 2: Concatenate segments ---"
CONCAT_FILE="$TMPDIR/concat.txt"
> "$CONCAT_FILE"
for i in "${!SEARCH_TERMS[@]}"; do
  echo "file $TMPDIR/seg_$i.webm" >> "$CONCAT_FILE"
done

# Step 3: Get total duration from last segment
read LAST_START LAST_END <<< $(get_srt_segment $((${#SEARCH_TERMS[@]}-1)))
TOTAL_DUR=$(python3 -c "print(round($LAST_END + 0.3, 2))")
echo "Total duration: ${TOTAL_DUR}s"

# Step 4: Concatenate, burn subtitles, merge audio
echo ""
echo "--- Step 3: Build final video ---"
ffmpeg -f concat -safe 0 -i "$CONCAT_FILE" \
  -i "$AUDIO" \
  -filter_complex \
    "[0:v]subtitles=$SRT:force_style='FontSize=16,FontName=Inter,PrimaryColour=&H00FFFFFF,BorderStyle=1,Outline=2,Shadow=0,MarginV=50'[vid]" \
  -map "[vid]" -map 1:a -t "$TOTAL_DUR" \
  -c:v libx264 -preset fast -crf 22 \
  "$OUTPUT_DIR/final-test.mp4" -y 2>&1 | tail -5

echo ""
echo "=== DONE ==="
echo "Output: $OUTPUT_DIR/final-test.mp4"
ffprobe -v quiet -show_entries format=duration,size -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_DIR/final-test.mp4"
