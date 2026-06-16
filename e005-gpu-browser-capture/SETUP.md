# e005 — Recording pipeline

## Prereqs

```bash
export DISPLAY=:99
export LIBVA_DRIVER_NAME=radeonsi
```

## Record (GPU encoding, 0 CPU)

```bash
# 1. Start virtual display
Xvfb :99 -screen 0 608x1080x24 &>/dev/null &

# 2. Open browser
google-chrome --no-sandbox --window-size=608,1080 --new-window "https://google.com" &

# 3. Record with VAAPI
ffmpeg -vaapi_device /dev/dri/renderD128 \
  -f x11grab -video_size 608x1080 -i :99.0 \
  -t 5 -vf "format=nv12,hwupload" -c:v h264_vaapi -b:v 4M \
  -y capture.mp4
```

5 seconds = 5 seconds real time. 1 MB per 5s. Zero CPU for encoding.
