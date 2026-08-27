#!/usr/bin/env bash
# vaapi_decode_test.sh — serve an H264 mp4 and have Chrome (port 9340) decode it.
set -u
PORT="${1:-9340}"
RES=/tmp/vaapi_test_result.txt
: > "$RES"
echo "start $(date)" >> "$RES"

pkill -f "http.server 9000" 2>/dev/null; sleep 1
python3 -m http.server 9000 --bind 127.0.0.1 --directory /tmp >/tmp/http9000.log 2>&1 &
SRV=$!
disown "$SRV"
sleep 1

curl -s -m 5 -o /dev/null -w "mp4_http=%{http_code}\n" http://127.0.0.1:9000/vaapi_test.mp4 >> "$RES"

agent-browser connect "$PORT" >>"$RES" 2>&1
agent-browser open "http://127.0.0.1:9000/vaapi_page.html" >>"$RES" 2>&1
sleep 4
echo "out_text: $(agent-browser eval 'document.getElementById("out").textContent' 2>&1 | tail -1)" >> "$RES"
echo "video_wh: $(agent-browser eval 'var v=document.getElementById("v"); v&&v.videoWidth?v.videoWidth+"x"+v.videoHeight:"NA"' 2>&1 | tail -1)" >> "$RES"
echo "dur: $(agent-browser eval 'var v=document.getElementById("v"); v&&v.duration?Math.round(v.duration*10)/10:0' 2>&1 | tail -1)" >> "$RES"

# Did decode hit the DRI render node? (VAAPI uses the render node.)
echo "dri_handles:" >> "$RES"
lsof /dev/dri/renderD128 2>/dev/null | grep -iE "chrome" | head -3 >> "$RES"

kill "$SRV" 2>/dev/null
echo "end $(date)" >> "$RES"
echo "=== RESULT FILE ==="
cat "$RES"
