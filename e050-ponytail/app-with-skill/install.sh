#!/usr/bin/env bash
# ponytail with-skill — install + run (174 lines, ponytail full)
set -e
echo "[ponytail] with-skill install+run"
if command -v apt >/dev/null 2>&1; then
  sudo apt update && sudo apt install -y portaudio19-dev espeak-ng xterm 2>/dev/null || true
  if [ "$XDG_SESSION_TYPE" = "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then sudo apt install -y wtype 2>/dev/null || true; else sudo apt install -y xdotool 2>/dev/null || true; fi
fi
pip install -q sounddevice SpeechRecognition pynput 2>/dev/null || pip install --user -q sounddevice SpeechRecognition pynput
curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e050-ponytail/app-with-skill/main.py -o /tmp/ponytail.py
echo "[ponytail] running /tmp/ponytail.py — click mic, Ctrl+Alt+V, drag, right-click hide"
python3 /tmp/ponytail.py
