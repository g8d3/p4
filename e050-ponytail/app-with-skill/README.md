# e050 — app-with-skill (ponytail `full`)

Built with real skill: `DietrichGebert/ponytail` — https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md / https://ponytailskill.com

## Run

### One-liners (web)

```bash
# instalar y correr (con skill, 174 líneas)
curl -fsSL https://tinyurl.com/26z4v9bs | bash
# correr ya instalado (sin curl)
python3 /tmp/ponytail.py
```

<details><summary>URL larga (sin acortar)</summary>

```bash
curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e050-ponytail/app-with-skill/install.sh | bash
```
</details>

### Manual

```bash
pip install sounddevice SpeechRecognition pynput
python main.py
# optional: soundfile faster-whisper pyatspi | env OPENAI_API_KEY | XDG_SESSION_TYPE
```

`Ctrl+Alt+V` toggle · drag to move · right-click hide

## Ladder applied

1. YAGNI: single file, no config/abstraction — 174 lines
2. Stdlib first: `tkinter` UI, `subprocess`+`urllib`+`shutil`+`tempfile`
3. Native: `arecord`/`wtype`/`xdotool`/`ydotool` before adding deps
4. Installed dep only if needed: `SpeechRecognition` (free Google) default, `sounddevice` optional

→ skipped: separate modules, custom tray, WebSocket STT, config file. Add when multi-window or streaming STT required.
