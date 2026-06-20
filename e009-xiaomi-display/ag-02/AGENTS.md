# ag-02 — Agent Studio: broadcast an agent's work live

A set of tools that any opencode agent can use to broadcast itself in real time: show its screen, speak its thoughts, and display subtitles.

This is NOT an agent that works. This is infrastructure. An agent (ag-01, ag-03, etc.) calls these tools while it works, and the user watches from their phone via a single URL.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, tmux conventions

## What the agent does with these tools

Any running opencode agent can do:

```bash
virt-display 1 720x1600          # start Xvfb + VNC on :1
python3 server/main.py &         # start web server (VNC + audio + subs)
DISPLAY=:1 firefox &             # run programs on the virtual display
subtitle "Buscando en Google..." # show a subtitle
speak "Encontré la solución"     # subtitle + TTS
```

The user opens ONE URL on their phone:
- Sees the virtual display (the agent's screen)
- Reads large subtitles of what the agent is doing
- Hears the agent speaking

## What ag-02 builds

### 1. Virtual display tools

Scripts to start/stop Xvfb + x11vnc + openbox on any display number.

### 2. Communication primitives

- `subtitle "text"` — shows a large caption at the bottom of the virtual display. Only shows the current/last message, not a scrollback. Font is big, readable from a phone.
- `speak "text"` — subtitle + TTS (edge-tts, Colombian voice). Audio streams through the same web URL.

### 3. Unified web server

Serves everything on one port (8080):
- HTML page with noVNC (browser VNC client)
- WebSocket proxy for VNC (binary frames only)
- Audio stream from PulseAudio (MP3, no visible controls, autoplay)
- Subtitle text endpoint
- Large, prominent subtitles on the page itself (so the user can read them even if the VNC canvas is small)

### 4. Clean HTML (NOT embedded in Python)

`server/static/index.html` is a separate file. The Python server reads it with `open().read()`. No HTML strings inside Python code.

## Design constraints

- **Subtitles are BIG**. Like movie captions, not a terminal log. 24px minimum on mobile. Semi-transparent overlay at the bottom of both the VNC canvas AND the HTML page.
- **Audio plays automatically**. No visible controls. Just a small indicator dot.
- **Mobile-first**. The page is designed for a phone held vertically. The VNC canvas scales to fit. Controls are minimal.
- **Everything on one URL**. `http://<host>:8080` shows screen + subtitles + audio.
- **Minimal Python files**. Each under ~80 lines. HTML is a separate file.
- **The agent who uses these tools writes its own commands**. ag-02 does not run any agent. It just provides the studio.

## Files to create

```
ag-02/
├── AGENTS.md
├── display/
│   ├── start.sh     # Xvfb + x11vnc + openbox on given display
│   └── stop.sh      # kill them
├── server/
│   ├── main.py      # aiohttp app (short, reads HTML file)
│   └── static/
│       └── index.html  # noVNC + big subtitles + audio (separate!)
├── subtitle.sh      # writes to subtitle endpoint
└── speak.sh         # calls subtitle.sh + edge-tts
```

## Common pitfalls

- x11vnc with `-bg` dies when the launching shell exits. Use `nohup` or avoid `-bg`.
- aiohttp `web.Response(content_type="text/plain; charset=utf-8")` fails. Use `content_type="text/plain", charset="utf-8"`.
- noVNC WebSocket proxy must send binary frames, not text.
- Audio autoplay is blocked on HTTP. Start with a silent AudioContext or accept one tap to enable.
- Chrome on Xvfb crashes without a window manager. Start openbox first.

## Self-command

```bash
tmux send-keys -t 9-2 "echo running" Enter
```
