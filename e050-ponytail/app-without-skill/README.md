# Dictation popup — WITHOUT ponytail skill (fair version)

Same spec as `../app-with-skill/` (floating mic button that records and types into any focused field on Linux), built **without reading the ponytail skill** and without any "intentionally bloated" instruction.

This is what a capable agent builds naturally when it doesn't climb the ponytail ladder:

- Still `tkinter` (stdlib) — most agents pick it anyway
- Extra `CONFIG_PATH` + `load_config()` JSON file that the task never asked for
- Three classes (`AudioRecorder`, `Transcriber`, `Typer`, `PopupApp`) instead of flat functions
- Single typing backend `xdotool` → `pynput` only, no `wtype`/`ydotool` and no `$XDG_SESSION_TYPE` Wayland auto-detect
- Google STT first, OpenAI second — but no `faster-whisper` local fallback
- No `pyatspi` auto-show, no `ponytail:` ceiling comments, no upgrade path
- Geometry persisted to `~/.config/dictation-popup/config.json` (YAGNI)
- 265 lines vs 207 with-skill — naturally more verbose, not caricatured

## Run

### One-liners (web)

```bash
# install and run (without skill, 265 lines)
curl -fsSL https://tinyurl.com/22sd6lw5 | bash
# run once installed (no curl)
python3 /tmp/dictation.py
```

<details><summary>Long URL (without shortener)</summary>

```bash
curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e050-ponytail/app-without-skill/install.sh | bash
```
</details>

### Manual

```bash
pip install sounddevice SpeechRecognition pynput
# system: sudo apt install xdotool portaudio19-dev  # + wtype on Wayland if needed
python main.py  # Ctrl+Alt+V toggle, Esc hide to taskbar (click to restore), drag to move
```

Contrast with `../app-with-skill/` which follows `DietrichGebert/ponytail` `full` (YAGNI → stdlib → native → installed dep → `ponytail:` comments).
