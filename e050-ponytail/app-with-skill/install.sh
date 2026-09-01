#!/usr/bin/env bash
# ponytail with-skill — install + run (174 lines, ponytail full)
# fast path: skips apt update unless --update passed; pip SSL fallback to apt
set -e
echo "[ponytail] with-skill install+run"
DO_UPDATE=""
[ "$1" = "--update" ] && DO_UPDATE=1
if command -v apt >/dev/null 2>&1; then
  if [ -n "$DO_UPDATE" ]; then echo "[ponytail] apt update..."; sudo apt update -qq 2>/dev/null || true; fi
  # install only if missing (fast, no update) — python3-tk is required for tkinter
  for pkg in portaudio19-dev espeak-ng xterm python3-tk; do dpkg -s "$pkg" >/dev/null 2>&1 || sudo apt install -y "$pkg" 2>/dev/null || true; done
  if [ "$XDG_SESSION_TYPE" = "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then dpkg -s wtype >/dev/null 2>&1 || sudo apt install -y wtype 2>/dev/null || true; else dpkg -s xdotool >/dev/null 2>&1 || sudo apt install -y xdotool 2>/dev/null || true; fi
  # apt fallback check (no loop needed, just ensure pip fallback below)
fi
# pip try; if SSL missing, fallback to apt
if ! pip install -q sounddevice SpeechRecognition pynput 2>/dev/null; then
  echo "[ponytail] pip SSL failed, trying apt fallback..."
  sudo apt install -y python3-sounddevice python3-pip 2>/dev/null || true
  pip install -q --trusted-host pypi.org --trusted-host files.pythonhosted.org sounddevice SpeechRecognition pynput 2>/dev/null || echo "[ponytail] pip still failed — run with apt python packages or fix python ssl"
fi
curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e050-ponytail/app-with-skill/main.py -o /tmp/ponytail.py
echo "[ponytail] running /tmp/ponytail.py — click mic, Ctrl+Alt+V, drag, right-click hide"
echo "[ponytail] fast update next time (no reinstall): curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e050-ponytail/app-with-skill/main.py -o /tmp/ponytail.py && python3 /tmp/ponytail.py"
# pyenv Python often lacks _tkinter/ssl — detect and fallback to system python3
if ! python3 -c "import _tkinter" 2>/dev/null; then
  echo "[ponytail] current python3 lacks _tkinter (pyenv without tk) — trying /usr/bin/python3..."
  if /usr/bin/python3 -c "import _tkinter" 2>/dev/null; then
    echo "[ponytail] using /usr/bin/python3 (has tkinter)"
    /usr/bin/python3 /tmp/ponytail.py
    exit 0
  else
    echo "[ponytail] no python with tkinter found. Fix: sudo apt install python3-tk tk-dev && pyenv install 3.9.7  # or use /usr/bin/python3"
    exit 1
  fi
fi
if ! python3 -c "import ssl" 2>/dev/null; then
  echo "[ponytail] current python3 lacks ssl — trying /usr/bin/python3..."
  /usr/bin/python3 /tmp/ponytail.py
  exit 0
fi
python3 /tmp/ponytail.py
