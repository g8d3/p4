# ag-04 — KasmVNC browser access to HEADLESS-1

Test KasmVNC as an alternative to noVNC for accessing HEADLESS-1 from a browser.

## Inherits
- [../ag-03/AGENTS.md](../ag-03/AGENTS.md) (virtual display setup, wayvnc)

## Architecture

```
Docker: kasmweb/desktop:1.16.0 (runs its own X11 desktop inside container)
  └── TigerVNC + KasmVNC UI → http://IP:8084

Alternatively: use KasmVNC .deb to connect to our wayvnc
```

## Docker test (kasmweb/desktop)

```bash
# Run container (X11 desktop + KasmVNC)
docker run --rm -d -p 8084:4902 --name kasm-test kasmweb/desktop:1.16.0

# Internal ports:
#   5901   VNC (TigerVNC, X11 desktop inside container)
#   6901   WebSocket RFB
#   4901   Audio WebSocket
#   4902   Web UI (upload server)
#   4903   Audio input
#   4904   Gamepad
#   8081   MPEG-TS audio stream
```

**Note**: this runs its own X11 desktop, not our HEADLESS-1. For connecting to wayvnc, see below.

## Local install (alternative)

```bash
# Download .deb from https://kasmweb.com/kasmvnc
sudo dpkg -i kasmvnc_*.deb

# Start KasmVNC web UI pointing to wayvnc
/usr/share/kasmvnc/geneneratessl.sh  # generate self-signed cert
kasmvnc_websockify \
  --web /usr/share/kasmvnc/www \
  --cert /home/$USER/.vnc/self.pem \
  8084 localhost:5900 &
```

## Findings

| Aspect | Docker container | Local install |
|--------|-----------------|---------------|
| Connects to... | its own X11 desktop | our HEADLESS-1 |
| Audio | Built-in (PulseAudio → ffmpeg → MPEG-TS) | Same |
| Port mapping | 4902 → web UI, 6901 → WS, 5901 → VNC | Configurable |
| Complexity | Medium (Docker networking) | Medium (needs .deb) |

## Compare with noVNC (ag-03)

| Feature | noVNC (ag-03) | KasmVNC |
|---------|---------------|---------|
| WebSocket proxy | wayvnc --websocket | Built-in in server |
| Audio | External ffmpeg endpoint | Built-in (PulseAudio → MPEG-TS) |
| File transfer | No | Yes |
| Clipboard | Text only | Bidirectional |
| UI polish | Basic | Professional + dark theme |
| Scaling | Manual CSS | Built-in responsive |
| Touch/mobile | Custom JS | Built-in |

## Ports (planned)

| Port | Service |
|------|---------|
| 5900 | wayvnc (HEADLESS-1) |
| 8084 | KasmVNC web UI |

## Próximo: ag-05 — Apache Guacamole
