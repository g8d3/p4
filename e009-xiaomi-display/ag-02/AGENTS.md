# ag-02 — Agent Viewer: watch an agent work on virtual display

Build a system where a user can watch an AI agent work in real time on a virtual display, hear it speak, and read subtitles of what it's thinking.

The user connects from their phone via a single URL. They see the virtual display, hear the agent's voice, and read its live commentary.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, tmux conventions

## What success looks like

1. A virtual X display (vertical, phone-like aspect ratio) runs on the server.
2. The user opens ONE URL in their phone browser and sees:
   - The virtual display contents (any program the agent runs: terminal, browser, file manager, etc.)
   - Large, readable subtitles at the bottom showing what the agent is doing/thinking
   - Hears the agent speaking via TTS (audio plays automatically, no play button)
3. Subtitles are BIG — like movie captions, not a log. The user should be able to read them from a phone without squinting.
4. The agent can TALK (TTS) and the user hears it through the same URL.
5. Everything on one port. One URL. No separate VNC client, no separate audio stream.

## Constraints

- **No HTML embedded in code**. HTML templates are separate `.html` files. Python serves them, does not contain them.
- **Mobile-friendly**: the web page must work on a phone portrait screen. The virtual display is vertical (e.g. 720×1600 or 540×1200). The VNC canvas should fill most of the screen.
- **Subtitles are NOT a log**. They should show the current/last thought, not a scrollback. Large font, semi-transparent overlay at the bottom of the screen.
- **Audio plays automatically**. No visible audio controls. Just a small indicator that audio is live.
- **Minimal but organized code**. Short files with clear names. No Python files longer than ~80 lines. No monolithic scripts.
- **The agent must be able to control programs on the virtual display**. It's not just a static screen — the agent (or another agent) runs commands there.

## Tools available

- `Xvfb` + `x11vnc` for the virtual display
- `openbox` as lightweight window manager
- `ffmpeg` for audio capture/streaming
- `edge-tts` for Text-to-Speech (Colombian voices: es-CO-SalomeNeural, es-CO-GonzaloNeural)
- `Python 3` with `aiohttp` or `websockets` for the web server
- `noVNC` (from CDN) for the browser VNC client
- `PulseAudio` / `PipeWire` for audio routing

## Common pitfalls

- VNC WebSocket proxy mixing text and binary frames. Send everything as binary.
- `x11vnc` dying when parent shell exits. Use `nohup` and `disown`, or avoid `-bg`.
- Chrome on Xvfb crashes without a window manager. Start `openbox` first.
- Audio autoplay blocked by browser on HTTP. Use an `AudioContext` resumed on user interaction, or accept that the first play needs a tap.
- Embedded HTML in Python makes editing painful. Put HTML in `.html` files, read them with `open().read()`.

## Files you need to create

Keep it minimal. This is a suggested structure, not a required one:

```
ag-02/
├── AGENTS.md
├── display/          # Virtual display + VNC tools
│   ├── start.sh      # Xvfb + x11vnc + openbox
│   └── stop.sh
├── server/           # Web server
│   ├── main.py       # aiohttp app, reads HTML files, serves WS proxy + audio
│   └── static/
│       └── index.html  # noVNC + subtitles + audio (separate file!)
└── speak.sh          # TTS + subtitle update in one command
```

## Self-command

```bash
tmux send-keys -t 9-2 "echo running" Enter
```
