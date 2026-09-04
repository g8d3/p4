# e050-ponytail — Voice Dictation Popup Experiment

Compare building the same Linux app **with vs without** the ponytail skill.

**Goal**: most concise Linux app where, when user is in any text field, a popup appears with a mic button; clicking it records voice and types transcription into the field.

## Structure

- `.agents/skills/ponytail/SKILL.md` (`skills/ponytail` → symlink) — ponytail methodology for ultra-concise single-file dictation popups (single source; `~/.agents/skills/ponytail` removed to avoid `name collision`)
- `app-with-skill/main.py` — 207 lines, ponytail `full` (real skill DietrichGebert/ponytail: YAGNI → stdlib `tkinter`/`urllib` → native `arecord`/`wtype`/`xdotool` → dep only if installed, `ponytail:` comments on caps, `pyatspi` 500ms poll degrade, error banner on STT/typing failures)
- `app-without-skill/main.py` — 265 lines, fair reference (same spec without ponytail ladder: `tkinter` but with extra `CONFIG_PATH`+`load_config()`, 4 classes vs flat functions, `xdotool`→`pynput` only no `wtype`/`ydotool` Wayland branch, no `ponytail:` ceilings)
- `comparison/COMPARISON.md` — side-by-side metrics

## Run

```bash
# concise (recommended)
pip install sounddevice SpeechRecognition pynput  # + sudo apt install xdotool or wtype
python e050-ponytail/app-with-skill/main.py

pip install sounddevice SpeechRecognition pynput
python e050-ponytail/app-without-skill/main.py  # fair version — same deps, but no Wayland `wtype`/`ydotool` branch, no `faster-whisper` fallback
```

## Skill usage

Agents building dictation popups must read `ponytail/SKILL.md` first. It enforces: single file ~200 lines, stdlib-first, pipe to system tools, pluggable STT, X11/Wayland auto-detect.
