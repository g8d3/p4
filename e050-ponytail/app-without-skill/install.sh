#!/usr/bin/env bash
# dictation without-skill — install + run (263 lines, fair)
set -e
echo "[dictation] without-skill install+run"
if command -v apt >/dev/null 2>&1; then
  sudo apt update && sudo apt install -y portaudio19-dev espeak-ng xterm xdotool 2>/dev/null || true
fi
pip install -q sounddevice SpeechRecognition pynput 2>/dev/null || pip install --user -q sounddevice SpeechRecognition pynput
curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e050-ponytail/app-without-skill/main.py -o /tmp/dictation.py
echo "[dictation] running /tmp/dictation.py"
python3 /tmp/dictation.py
