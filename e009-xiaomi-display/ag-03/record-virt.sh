#!/bin/bash
OUTPUT="${1:-recording-$(date +%s)}"
DIR="/tmp/record-$$"
mkdir -p "$DIR"
MONITOR="alsa_output.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.analog-stereo.monitor"
VOLUME=200

set_volume() {
    pactl set-source-volume "$MONITOR" "$1%" 2>/dev/null
    VOLUME=$1
}

stop_all() {
    kill "$VIDEO_PID" "$AUDIO_PID" 2>/dev/null
    wait 2>/dev/null
}

merge() {
    echo "Merging..."
    ffmpeg -i "$DIR/video.mp4" -i "$DIR/audio.aac" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest -y "$OUTPUT.mp4" 2>/dev/null
    echo "Saved: $OUTPUT.mp4 ($(du -h "$OUTPUT.mp4" | cut -f1))"
}

finish() {
    trap '' INT TERM
    stop_all
    set_volume 100
    merge
    rm -rf "$DIR"
    exit 0
}

trap finish INT TERM

set_volume 200
WAYLAND_DISPLAY=wayland-1 wf-recorder -o HEADLESS-1 -f "$DIR/video.mp4" > /dev/null 2>&1 &
VIDEO_PID=$!
ffmpeg -f pulse -i "$MONITOR" -c:a aac -b:a 192k -y "$DIR/audio.aac" > /dev/null 2>&1 &
AUDIO_PID=$!

echo "Recording to $OUTPUT.mp4"
echo "  + / -   volume (±25)"
echo "  s       status"
echo "  q       stop & save"
echo "  Ctrl+C  stop & save"
echo "---"

while true; do
    read -rsn1 key
    case "$key" in
        +|=) new=$((VOLUME + 25)); [ "$new" -le 500 ] && set_volume "$new"; echo "Volume: ${VOLUME}%" ;;
        -|_) new=$((VOLUME - 25)); [ "$new" -ge 25 ] && set_volume "$new"; echo "Volume: ${VOLUME}%" ;;
        s) echo "Volume: ${VOLUME}%  |  video=$VIDEO_PID audio=$AUDIO_PID" ;;
        q|Q) finish ;;
    esac
done
