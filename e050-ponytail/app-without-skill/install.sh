#!/usr/bin/env bash
# dictation without-skill — install + run (263 lines, fair)
set -e
echo "[dictation] without-skill install+run"
DO_UPDATE=""; [ "$1" = "--update" ] && DO_UPDATE=1
if command -v apt >/dev/null 2>&1; then
  if [ -n "$DO_UPDATE" ]; then echo "[dictation] apt update..."; sudo apt update -qq 2>/dev/null || true; fi
  for pkg in portaudio19-dev espeak-ng xterm xdotool python3-tk; do dpkg -s "$pkg" >/dev/null 2>&1 || sudo apt install -y "$pkg" 2>/dev/null || true; done
fi
NEED_PIP=0; python3 -c "import sounddevice, speech_recognition" 2>/dev/null || NEED_PIP=1; /usr/bin/python3 -c "import sounddevice, speech_recognition" 2>/dev/null && NEED_PIP=0
if [ "$NEED_PIP" = "1" ]; then
  if ! pip install -q sounddevice SpeechRecognition pynput 2>/dev/null; then
    echo "[dictation] pip SSL failed, trying apt + system pip fallback..."
    dpkg -s python3-sounddevice >/dev/null 2>&1 || sudo apt install -y python3-sounddevice 2>/dev/null || true
    if /usr/bin/python3 -m pip install -q SpeechRecognition pynput 2>/dev/null; then echo "[dictation] installed via /usr/bin/python3 -m pip"; else pip install -q --trusted-host pypi.org --trusted-host files.pythonhosted.org sounddevice SpeechRecognition pynput 2>/dev/null || echo "[dictation] pip still failed — using apt packages"; fi
  fi
else
  echo "[dictation] pip deps already present, skipping"
fi
curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e050-ponytail/app-without-skill/main.py -o /tmp/dictation.py
echo "[dictation] running /tmp/dictation.py"
echo "[dictation] fast update next time: curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e050-ponytail/app-without-skill/main.py -o /tmp/dictation.py && python3 /tmp/dictation.py"
if ! python3 -c "import _tkinter" 2>/dev/null; then
  echo "[dictation] current python lacks _tkinter — trying /usr/bin/python3..."
  if /usr/bin/python3 -c "import _tkinter" 2>/dev/null; then /usr/bin/python3 /tmp/dictation.py; exit 0; else echo "[dictation] fix: sudo apt install python3-tk tk-dev && pyenv install 3.9.7"; exit 1; fi
fi
if ! python3 -c "import ssl" 2>/dev/null; then /usr/bin/python3 /tmp/dictation.py; exit 0; fi
python3 /tmp/dictation.py
