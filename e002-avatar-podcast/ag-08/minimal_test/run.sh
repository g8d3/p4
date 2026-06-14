#!/bin/bash
set -e
export LIBVA_DRIVER_NAME=radeonsi
cd "$(dirname "$0")"
rm -f test_pipe
mkfifo test_pipe

timeout 30 ffmpeg -f rawvideo -pix_fmt rgba -s 608x1080 -framerate 25 \
  -i test_pipe \
  -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y minimal_output.mp4 &
FFPID=$!

timeout 30 godot4 --rendering-driver vulkan --display-driver headless \
  --path .

wait $FFPID 2>/dev/null
rm -f test_pipe
touch done.txt
echo "RENDER COMPLETE"
