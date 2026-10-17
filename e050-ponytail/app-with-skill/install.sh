#!/usr/bin/env bash
# ponytail with-skill — install + run (207 lines, ponytail full)
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
# pip try only if needed; if SSL missing, fallback to apt (check installed first)
NEED_PIP=0; python3 -c "import sounddevice, speech_recognition" 2>/dev/null || NEED_PIP=1; /usr/bin/python3 -c "import sounddevice, speech_recognition" 2>/dev/null && NEED_PIP=0
if [ "$NEED_PIP" = "1" ]; then
  if ! pip install -q sounddevice SpeechRecognition pynput 2>/dev/null; then
    echo "[ponytail] pip SSL failed, trying apt + system pip fallback..."
    dpkg -s python3-sounddevice >/dev/null 2>&1 || sudo apt install -y python3-sounddevice 2>/dev/null || true
    dpkg -s python3-pip >/dev/null 2>&1 || sudo apt install -y python3-pip 2>/dev/null || true
    # use system python pip (has ssl) instead of pyenv pip
    if /usr/bin/python3 -m pip install -q SpeechRecognition pynput 2>/dev/null; then
      echo "[ponytail] installed SpeechRecognition via /usr/bin/python3 -m pip"
    else
      echo "[ponytail] system pip also failed — trying curl wheel fallback..."
      curl -fsSL https://files.pythonhosted.org/packages/aa/e7/13e260a9cb53a40177783a882ebdfa437b2414fa21ca6f1cb8d9043b3fc9/speechrecognition-3.17.0-py3-none-any.whl -o /tmp/sr.whl 2>/dev/null && /usr/bin/python3 -m pip install -q /tmp/sr.whl 2>/dev/null && echo "[ponytail] installed via curl wheel" || pip install -q --trusted-host pypi.org --trusted-host files.pythonhosted.org sounddevice SpeechRecognition pynput 2>/dev/null || echo "[ponytail] pip still failed — using apt python packages"
    fi
  fi
else
  echo "[ponytail] pip deps already present, skipping"
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
