# avatar-server protocol contract (de-facto, v1.0)

Shared control protocol for e030 VRM Avatar. Server: `avatar-server`
(Node, `server.js`) on `127.0.0.1:8787` (binds `0.0.0.0`). Owned by ag-01;
patched cooperatively by ag-02 (client-B routes + cmdResponse resolution).

## Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | client-A viewer (`viewer.html`) |
| `/viewer-b.html` | GET | client-B viewer (served from `../ag-02-client-b/`) |
| `/client-b/*` | GET | client-B static assets (dist bundle) |
| `/vendor/*` | GET | npm modules served from `./node_modules/` (importmap base) |
| `/models/<file>` | GET | VRM/GLB files from `../models/` |
| `/media/<file>` | GET | speech audio + `*.mouth.json` from `../media/` (falls back to `../ag-03-video/output/`) |
| `/health` | GET | `{"ok":true,"server":"avatar-server","protocol":"1.0","clients":[...],"pid":...}` |
| `/cmd` | POST | Issue one command (JSON body); responds when the client(s) reply (20 s timeout) |
| `/` (WS) | WS | Registration + command transport |

## Client registration

1. Client opens WS `ws://<host>/` and receives `{"type":"hello","server":"avatar-server","protocol":"1.0"}`.
2. Client sends `{"type":"register","id":"<clientId>"}` (e.g. `clientA`, `B`).
3. Server acks `{"type":"registered","id":"<clientId>",...}`.
4. Multiple WS connections may register the same id; commands fan out to all of them.

## Commands (JSON)

A command is `{"cmd":"<name>", ...payload, "client":"all"|"<id>"}`.
- `client` defaults to `all`; a specific id targets only that client.
- Server wraps and forwards to clients as
  `{"type":"cmd","cmd":"<name>","cmdId":"...", ...payload}`.
- Client replies `{"type":"cmdResponse","cmdId":"...","cmd":"<name>","clientId":"<id>", "ok":true/false, ...result}`.
- HTTP `POST /cmd` resolves when all targeted clients respond (or 20 s timeout):
  response mirrors the command plus `ok`, `cmdId`, `client`, `responses[]`.

| Command | Payload | Effect / result |
|---|---|---|
| `load` | `{"model":"models/<file>.vrm"}` | Load VRM; returns `ok, model, name, version` |
| `expression` | `{"name":"happy","weight":1}` | Set expression weight; returns `name, weight` (errors list `available` names) |
| `resetExpression` | `{}` | Zero all expression weights; returns `ok` |
| `lookAt` | `{"x":0.4,"y":0.2}` | Set normalized look-at target; returns `x, y` |
| `bone` | `{"name":"leftUpperArm","rotate":[0,0.5,0]}` | Direct humanoid bone rotation (rad); returns applied `rotate` |
| `animation` | `{"url":"...","loop":true}` | Play VRMA/GLB animation; returns `url, loop, format` |
| `speak` | `{"audio":"media/<f>.mp3","mouth":"media/<f>.mouth.json"}` | Play audio + drive mouth/`aa` from `[[t_ms,weight],...]`; returns `points` count |
| `setIdle` | `{"on":true}` | Enable/disable idle blink + breathing; returns `on` |
| `inspect` | `{}` | Model state: meta, humanoid bones, expressions (names/weights), spring bones, renderer info, camera, lookAt |
| `ping` | `{}` | `{"ok":true,"pong":true}` |

## Lip sync

`mouth.json` is `[[t_ms, weight], ...]` (100 ms windows from RMS energy, per e000
fundamentals). Clients interpolate linearly and apply the weight to the
`mouth` expression if present, else `aa`. Client-A default mouth expression:
`aa` (VRM1_Constraint_Twist_Sample).

## Client-A (ag-01) notes

- Importmap serves `three`, `three/addons/`, `@pixiv/three-vrm`,
  `@pixiv/three-vrm-animation` from `/vendor/`.
- Camera: PerspectiveCamera fov 42, 608×1080 vertical, `(0,1.35,1.85)` → `(0,1.25,0)`.
- Idle: blink (blink/blinkLeft/blinkRight), chest breathing, look-at wander.
- WebGL2 renderer; inspected version pair: `three` r185, `@pixiv/three-vrm` 3.5.5.