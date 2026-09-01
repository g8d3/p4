#!/usr/bin/env bash
# dictation without-skill — install + run (263 lines, fair)
set -e
echo "[dictation] without-skill install+run"
DO_UPDATE=""; [ "$1" = "--update" ] && DO_UPDATE=1
if command -v apt >/dev/null 2>&1; then
  if [ -n "$DO_UPDATE" ]; then echo "[dictation] apt update..."; sudo apt update -qq 2>/dev/null || true; fi
  for pkg in portaudio19-dev espeak-ng xterm xdotool; do dpkg -s "$pkg" >/dev/null 2>&1 || sudo apt install -y "$pkg" 2>/dev/null || true; done
fi
if ! pip install -q sounddevice SpeechRecognition pynput 2>/dev/null; then
  echo "[dictation] pip SSL failed, trying apt fallback..."
  sudo apt install -y python3-sounddevice python3-pip 2>/dev/null || true
  pip install -q --trusted-host pypi.org --trusted-host files.pythonhosted.org sounddevice SpeechRecognition pynput 2>/dev/null || echo "[dictation] pip still failed — fix python ssl or use apt packages"
fi
curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e050-ponytail/app-without-skill/main.py -o /tmp/dictation.py
echo "[dictation] running /tmp/dictation.py"
echo "[dictation] fast update next time: curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e050-ponytail/app-without-skill/main.py -o /tmp/dictation.py && python3 /tmp/dictation.py"
python3 /tmp/dictation.py
