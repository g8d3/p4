#!/bin/bash
usage() { echo "Usage: $0 [-n <seconds>] [-l <logfile>] [output-name]"; exit 1; }

SAMPLE_INTERVAL=0
LOGFILE=""
while getopts "n:l:h" opt; do
    case "$opt" in
        n) SAMPLE_INTERVAL="$OPTARG" ;;
        l) LOGFILE="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done
shift $((OPTIND-1))
OUTPUT="${1:-recording-$(date +%s)}"
DIR="/tmp/record-$$"
mkdir -p "$DIR"
MONITOR="alsa_output.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.analog-stereo.monitor"
VOLUME=200
START=$(date +%s)

log() {
    [ -n "$LOGFILE" ] && echo "$(date '+%H:%M:%S') $*" >> "$LOGFILE"
}

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
    log "saved $OUTPUT.mp4"
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
[ -n "$LOGFILE" ] && echo "Log: $LOGFILE"
echo "  + / -   volume (+-25)"
echo "  s       resource usage"
echo "  q       stop & save"
echo "  Ctrl+C  stop & save"
echo "---"
log "start -> $OUTPUT.mp4"

status() {
    local dur=$(($(date +%s) - START))
    local vsize=$(du -h "$DIR/video.mp4" 2>/dev/null | cut -f1)
    local asize=$(du -h "$DIR/audio.aac" 2>/dev/null | cut -f1)
    local vcpu=$(ps -p $VIDEO_PID -o %cpu= 2>/dev/null || echo "?")
    local vmem=$(ps -p $VIDEO_PID -o rss= 2>/dev/null | awk '{printf "%.0f", $1/1024}' || echo "?")
    local acpu=$(ps -p $AUDIO_PID -o %cpu= 2>/dev/null || echo "?")
    local amem=$(ps -p $AUDIO_PID -o rss= 2>/dev/null | awk '{printf "%.0f", $1/1024}' || echo "?")
    printf "[Video] wf-recorder  CPU: %5s%%  MEM: %4sM  Size: %s\n" "$vcpu" "$vmem" "$vsize"
    printf "[Audio] ffmpeg       CPU: %5s%%  MEM: %4sM  Size: %s\n" "$acpu" "$amem" "$asize"
    printf "-------------------------------------------\n"
    printf "Duration: %ds  Volume: %d%%\n" "$dur" "$VOLUME"
    log "dur=${dur}s vol=${VOLUME}% video_cpu=${vcpu}% video_mem=${vmem}M audio_cpu=${acpu}% audio_mem=${amem}M"
}

read_key() {
    local timeout="$1"
    if [ -n "$timeout" ]; then
        read -rsn1 -t "$timeout" key
    else
        read -rsn1 key
    fi
    return $?
}

handle_key() {
    case "$1" in
        +|=) local n=$((VOLUME + 25)); [ "$n" -le 500 ] && set_volume "$n"; echo "Volume: ${VOLUME}%" ;;
        -|_) local n=$((VOLUME - 25)); [ "$n" -ge 25 ] && set_volume "$n"; echo "Volume: ${VOLUME}%" ;;
        s) status ;;
        q|Q) finish ;;
    esac
}

while true; do
    if [ "$SAMPLE_INTERVAL" -gt 0 ]; then
        read_key "$SAMPLE_INTERVAL" && handle_key "$key" || status
    else
        read_key && handle_key "$key"
    fi
done
