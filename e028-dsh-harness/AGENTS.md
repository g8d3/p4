# e028 — DeepSeek Harness (dsh) web: install, LAN access, and security fences

Experiment documenting how to get **DeepSeek Harness** running on this machine
and reachable from the LAN. The value is not the happy path (`npx @deepseek-ai/dsh web`
does not work out of the box) — it is the five traps found and verified:

1. npm 12 blocks install scripts → native `pty.node` never builds
2. `--host 0.0.0.0` is intentionally rejected → LAN needs a reverse proxy
3. `crypto.randomUUID` dies on plain HTTP LAN origins (not a secure context)
4. `/api` returns HTTP 403 on LAN → `--trusted-host` fence
5. `settings.describe` (and friends) are loopback-only **by design** → SSH tunnel

## What is dsh

[DeepSeek Harness](https://github.com/deepseek-ai/dsh) — a browser UI for the
DeepSeek agent harness. Local web app: `npx @deepseek-ai/dsh web` serves a UI on
`127.0.0.1:3080` with agent workspaces, filesystem browsing, model/settings
panels, and remote code execution on the host machine.

Because it can execute code on the host, its security model is **aggressively
loopback-first**: it refuses LAN binds, validates every `/api` request against a
browser-trust fence, and pins all privileged configuration endpoints to
loopback origins regardless of `--trusted-host`.

## Repo layout

| Path | What |
|---|---|
| `app/package.json` | Working install manifest with the approved `allowScripts` block (committed) |
| `app/node_modules/` | Installed packages, **gitignored** |
| `bin/install.sh` | Full install: npm install + allowScripts approval + rebuild + verify |
| `bin/start.sh` | Start dsh + HTTP/TLS reverse proxies |
| `bin/stop.sh` | Stop everything by PID |
| `bin/gen-cert.sh` | Self-signed TLS cert for the LAN HTTPS proxy |
| `profiles/opencode-default.yml` | Default provider+model from `OPENCODE_*` env (`--patch` overlay applied by `bin/start.sh`) |
| `bin/check.sh` | Self-test replicating a phone browser (listeners, 401/403/200/302 assertions, both phone traps); exit 1 on anything a user would feel |
| `bin/e2e.mjs` | Deep E2E: real headless Chrome (phone viewport) + virtual passkey authenticator through every portal button/input, then the live dsh UI (inventory, view tour, typing, terminal echo). `node bin/e2e.mjs [--portal\|--dsh]`; screenshots to `/tmp/dsh-e2e-*` |
| `bin/act.mjs` | Act visibly inside the app: creates a session via the UI's New Session button, types a task, submits, waits, prints the chat tail. `node bin/act.mjs "<task>"` — the user watches live on :9444 |
| `portal/server.mjs` | Password + passkey (WebAuthn) accounts + invites + admin (stdlib only, port 8090) — no terminal needed |
| `portal/webauthn.mjs` | Dependency-free WebAuthn core: CBOR, COSE→JWK, attestation-none registration, assertion verify |
| `portal/.pass.json` | Portal password (scrypt hash, 0600, **gitignored**) |
| `cert/` | Generated cert, **gitignored** |
| `log/` | Runtime logs, incl. `client-errors.log` — the phone-error inbox (each line a `derr_` ref shown on the failing page) + `.client-errors.cursor` (what the operator already processed) |

## Install (the npm 12 trap)

`npx @deepseek-ai/dsh web` fails with:

```
Error: Failed to load native module: pty.node, checked: build/Release,
build/Debug, prebuilds/linux-x64
```

**Root cause**: `node-pty` ships prebuilds only for darwin/win32 — linux must
compile from source during `npm install`. npm 12's `allowScripts` security
feature blocks install scripts by default, so the build never ran. The npx
cache path cannot be fixed per-package; install into a real project instead:

```sh
mkdir app && cd app && npm init -y
npm install @deepseek-ai/dsh
npm install-scripts approve node-pty koffi @deepseek-ai/dsh-subprocess-local
npm rebuild node-pty
```

The `approve` step writes an `allowScripts` block into `package.json` — which is
**committed** (only `node_modules/` is gitignored), so `npm install` in a fresh
clone re-runs the scripts without re-approving. `bin/install.sh` wraps the
whole flow and verifies `pty.node` exists before finishing. Verify the binary
exists before starting (path depends on version):

```sh
# dsh 0.1.x (node-pty 1.1.0, compiled from source):
ls node_modules/node-pty/build/Release/pty.node   # must exist
# dsh 0.2.x (node-pty 1.2.x ships linux prebuilds, no compile needed):
ls node_modules/node-pty/prebuilds/linux-x64/pty.node   # must exist
```

> 2026-10-18: bumped to dsh 0.2.1-rc.2 (npm tag `next`; `latest` is still
> 0.2.0-rc.2). Same three approvals at new versions, prebuild used, no
> compile. `bin/install.sh` takes an optional spec (default
> `@deepseek-ai/dsh@next`); pinned version recorded in `needs.json`.
>
> 2026-10-05: after updating to dsh 0.2.0-rc.2, four packages asked for
> approval (`node-pty`, `koffi`, `@deepseek-ai/dsh-subprocess-local`, plus
> no-op scripts in `@google/genai`/`protobufjs` which were left denied).
> No compilation ran — the linux-x64 prebuild was used. If `build/Release/`
> is absent but `prebuilds/linux-x64/pty.node` exists, that is fine.

Three packages needed approval on this machine: `node-pty` (pty support),
`koffi` (native FFI), `@deepseek-ai/dsh-subprocess-local` (subprocess helper).

## Local run

```sh
npx dsh web          # → http://127.0.0.1:3080
```

Full functionality works here: the browser origin is loopback, which satisfies
the trust fence AND the privileged-method gate.

## LAN access (traps 2–5)

### Trap 2: dsh refuses LAN binds

- `dsh web --host 0.0.0.0` → hard error: *"intentionally not supported yet for
  safety: it would expose remote code execution to the network"*.
- `dsh web --host 192.168.0.93` → config validation rejects anything except
  `127.0.0.1` / `0.0.0.0`.

So LAN exposure must go through a reverse proxy. **Use a different port than
3080**: dsh's listener occupies the port such that a wildcard bind of the same
port fails with EADDRINUSE (verified empirically — it is not normal socket
behavior, but it is reproducible).

```sh
nohup socat -4 TCP-LISTEN:8080,fork,reuseaddr TCP:127.0.0.1:3080 &
```

### Trap 3: crypto.randomUUID is not a function

The browser client calls `crypto.randomUUID()` (dsh-client-connection
`lib/client.js`). Browsers only define it in **secure contexts** (HTTPS or
localhost). Plain HTTP on a LAN IP is not one → the UI breaks. Serve over HTTPS
with a self-signed cert:

```sh
openssl req -x509 -newkey rsa:2048 -keyout dsh-key.pem -out dsh-cert.pem \
  -days 365 -nodes -subj "/CN=192.168.0.93"
cat dsh-cert.pem dsh-key.pem > dsh.pem
nohup socat -4 openssl-listen:8443,fork,reuseaddr,cert=dsh.pem,verify=0 \
  TCP:127.0.0.1:3080 &
```

HTTPS covers every secure-context-only browser API, not just `randomUUID`.

### Trap 4: HTTP 403 on /api — the browser-trust fence

dsh validates every `/api` request against a DNS-rebinding + cross-site fence
(`isTrustedApiRequest`, dsh-client-connection `lib/index.js`): the `Host`
header must be loopback or a declared trusted host, and any `Origin` must match.
Trust LAN origins with the CLI flag (value must equal the **browser origin**,
`host:port`):

```sh
npx dsh web --trusted-host 192.168.0.93:8443
```

### Trap 5: privileged methods stay loopback-only — by design

Even with `--trusted-host`, these return 403 from a LAN origin
(`PRIVILEGED_METHODS`, dsh-client-connection `lib/index.js:498`):

```
agentPreset.*, host.pickDirectory, host.openPath,
settings.describe|openDocument|update|replace|mutate,
credentials.describe|set|unset, llm.discoverModels
```

The dsh source is explicit: `trustedHosts` is a DNS-rebinding fence, **not
authentication**, so the whole configuration plane stays loopback-same-origin
until a real auth layer exists. This cannot be configured away.

**The only way to get full functionality from another machine**: SSH tunnel, so
the browser's origin is loopback:

```sh
ssh -L 3080:127.0.0.1:3080 <user>@192.168.0.93
# then open http://127.0.0.1:3080 — everything works
```

## Portal: web access without touching the terminal

`portal/server.mjs` (Node stdlib, HTTPS on `0.0.0.0:8090` with the same
self-signed cert) fronts the per-boot dsh token with **user accounts**:

1. Open the portal, log in (passkey or recovery password).
2. Press **Open dsh** → 302 to the dsh authority matching how you arrived
   (tailnet `:<ts_dsh_port>` or LAN `:<lan_tls>`) with this boot's `?token=…`
   (read live from `log/dsh.log`, so it survives dsh restarts).

### Passkeys (primary login)

WebAuthn `rpId` must be a real hostname — bare IPs always fail — so passkeys
only work via the tailnet URL `https://<public_host>:<ts_portal_port>`
(real trusted cert via `tailscale serve`, tailnet-only, no funnel). The LAN-IP
page keeps the password flow and points passkey users at the public URL.

- **First account:** with an empty user DB, `/register` on the public URL
  creates the **admin** (no invite needed). Afterwards: admin creates
  single-use **invite links** (`/admin`); each link yields one account.
- Users can enroll multiple devices (account page → “Register passkey on this
  device”), remove keys, and see all users/invites in `/admin`.
- Server verifies rpId, origin, challenge, signature, and sign-counter
  (clone detection); attestation is `none` (TOFU on a private tailnet —
  documented tradeoff, not a bug).
- The shared password stays as **break-glass recovery** (also admin); it can
  be changed from the portal itself, never the terminal.

Verified 2026-10-05: crypto core against a simulated P-256 credential
(register/assert OK; forged signature and wrong rpId rejected); live
plumbing (public-host gating, challenge issuance with correct rpId,
stale-challenge rejection); full chain portal→dsh token exchange over both
LAN and tailnet. Real authenticator enrollment happens on the user's device.

Machine values (ports, hosts, files) are documented in `needs.json`.

## Setting provider keys without the web UI

The web Models page is loopback-only (trap 5), but it is not the only way to
set keys — and on this machine it is not even the primary one. Verified
2026-08-15:

- `deepseek-official` (default provider) resolves its key from
  `~/.dsh/.credentials.yaml` via the credentials service, falling back to the
  `DEEPSEEK_API_KEY` env var (dsh-llm-deepseek `resolveApiKey`). The credentials
  file is a strict `CredentialRef: string` YAML map, owner-only (0600):

  ```yaml
  DEEPSEEK_API_KEY: sk-xxxx
  ```

  This file is exactly what the web Models page writes; both layers hot-publish
  without a restart (file writes re-load under a lock; env requires relaunching
  dsh).
- On this machine the key already comes from the environment — verify headlessly
  (loopback origin needed for the fence):

  ```sh
  curl -s -H "Origin: http://127.0.0.1:3080" -H "Content-Type: application/json" \
    -X POST http://127.0.0.1:3080/api/credentials.describe \
    -d '{"type":"client-request","rpcId":"r","method":"credentials.describe","payload":{"refs":["DEEPSEEK_API_KEY"]}}'
  # → "configured": true, "source": "env"
  ```

  So the provider directory failing to load over LAN is cosmetic: the provider
  itself is already configured and usable headlessly. Only the settings/Models
  web page needs a loopback origin (SSH tunnel).

## Working topology

```
┌─ LAN machine ──────────────────────────────────────────────────┐
│  http://192.168.0.93:8080  (plain HTTP, non-privileged only)   │
│  https://192.168.0.93:8443 (secure context, non-privileged)    │
│  ssh -L 3080 → http://127.0.0.1:3080  (full)                   │
└────────────────────────────────────────────────────────────────┘
                            │
               0.0.0.0:8080 (HTTP)  /  0.0.0.0:8443 (TLS)
                            ▼
                     socat proxies
                            ▼
               127.0.0.1:3080  dsh web --trusted-host 192.168.0.93:8443
```

`bin/start.sh` brings up the whole stack; `bin/stop.sh` takes it down by PID.

## Verify (don't assume)

```sh
# dsh + proxies listening
ss -tlnp | grep -E '3080|8080|8443'

# fence: same headers, listDirectory passes, settings.describe 403 on LAN
curl -sk -o /dev/null -w "%{http_code}\n" \
  -H "Host: 192.168.0.93:8443" -H "Origin: https://192.168.0.93:8443" \
  -H "Content-Type: application/json" -H "sec-fetch-site: same-origin" \
  -X POST https://192.168.0.93:8443/api/host.listDirectory -d '{"path":"./"}'   # 200
# same request for /api/settings.describe → 403 (expected, by design)
```

## Security notes

- The proxies bypass dsh's localhost-only bind — the web UI can run code on the
  host. Use only on a trusted LAN; the HTTPS proxy still self-signed (MITM).
- Never expose plain `http://…:8080` beyond a trusted LAN (no transport
  security, same RCE surface).
- `--trusted-host` grants the fence, not authentication: any LAN client with
  the right origin headers can call non-privileged APIs.

## Experiment goals

1. **Documented, reproducible setup** — install + LAN topology captured in
   `bin/*.sh` and this AGENTS.md.
2. **Explain the five traps** with root causes (source files + line numbers).
3. **Working full access from mobile** (the p4 working environment): SSH tunnel
   gives loopback origin on the phone's browser.

## Update 2026-10-05: dsh 0.2.0-rc.2 (was 0.1.0-rc.6)

Update: `npm install "@deepseek-ai/dsh@latest"` in `app/`, re-approve scripts,
`npm rebuild node-pty`. (`bin/install.sh` still exits early when
`app/node_modules` exists — updates are manual.)

What changed (verified live + upstream docs at
`github.com/deepseek-ai/deepseek-harness`):

- **Trap 5 is gone — replaced by launch-token auth.** Every RPC method and
  the WS stream now require the same browser session; there is no
  method-specific loopback tier. Each boot mints a random token, printed once
  as a `?token=…` URL (`log/dsh.log`). Opening it sets a signed,
  authority-bound (`host:port`) cookie (`HttpOnly`, `SameSite=Strict`, **no**
  `Secure`, 30-day default) and redirects to clean `/`. Consequences:
  - The startup `?token=…` URL is now a **credential** — never paste it into
    chats/logs. Each browser/device needs the exchange once; each authority
    (`127.0.0.1:3080` vs `lan:8443` vs `lan:8080`) needs its **own**
    exchange (cookies are authority-bound — verified: a cookie minted on
    `:8443` gets 401 on `:8080`).
  - Status-code semantics: fence failure → **403**, trusted-but-unauthenticated
    → **401**, admitted-but-unknown-method → **404**. Verified live:
    `GET /` without cookie → 401, with cookie → 200 + app HTML;
    `POST /api/<stale-method>` with cookie → 404 (passed fence AND auth,
    name no longer exists).
  - No logout exists; global revocation = delete the
    `client-connection/browser-session` record in `$DSH_HOME/.credentials.yaml`
    **and** restart.
- **Traps 2 and 4 unchanged.** `--host 0.0.0.0` still rejected at startup;
  specific-LAN-IP bind still rejected by the webserver schema (open Idea
  upstream, no commitment). Reverse proxy stays mandatory. `--trusted-host`
  still required for proxied LAN origins — reachability only, not auth.
- **Trap 3: keep HTTPS.** Unverified whether the client dropped the
  `randomUUID` call; upstream explicitly warns the cookie omits `Secure`, so
  plaintext-LAN exposure leaks a bearer capable of the full tool API.
  Prefer `https://<lan>:8443`; treat `http://<lan>:8080` as trusted-LAN-only.
- **RPC endpoint names moved.** Old names (`host.listDirectory`,
  `settings.describe`, `credentials.describe`) now 404 even authenticated —
  the Typert Gateway claims generated Remote endpoints. Re-discover names
  from the client before scripting `/api` by hand.
- **New flag:** `--public-url` (v0.2.1-alpha.1) sets the displayed/opened/
  model-facing address, incl. reverse proxies with a path prefix.
- **Scripts now auto-detect the LAN IP** (`hostname -I`) instead of the stale
  `192.168.0.93` default — pass an explicit IP to `bin/start.sh` to override.
  The committed self-signed cert still carries the old CN (harmless:
  browsers warn on self-signed either way; delete `cert/dsh.pem` to regen).

## Update 2026-10-18: dsh 0.2.1-rc.2 + any-IP access (verified live)

- **Version:** `app/` moved `latest` → `next` (0.2.0-rc.2 → 0.2.1-rc.2).
  `dsh web --help` deltas: `--host` now takes one concrete interface
  literal (wildcards still rejected — socat stays mandatory); new
  `--public-url` (advertise only, grants no trust) and native
  `--tls-cert/--tls-key`. Topology unchanged by choice: one dsh boot =
  one launch token, and socat keeps a single origin for HTTP + TLS +
  tailnet-serve.
- **Any-IP:** `bin/start.sh` now passes `--trusted-host` for every browser
  origin: LAN IP (bare + `:8080`/`:8443`), tailscale IP (bare + ports),
  tailnet MagicDNS host (bare + `:9444`). socat/portal were already
  `0.0.0.0`-bound; the missing piece was the fence, not the bind.
- **Verified 2026-10-18:** `GET /` without cookie → 401 on LAN `:8080`,
  LAN `:8443`, tailnet-IP `:8443`, tailnet `:9444`; `/api` with evil
  `Origin` → 403 (fence holds), with trusted `Origin` → 401 (auth gate
  holds); portal 200 on LAN `:8090` and tailnet `:9443`; `/open`
  logged-out → 302 to login (token never leaks).

## Self-test (so no human has to be the tester)

`bin/check.sh` replays exactly what a phone browser does — same URLs, same
TLS+SNI, same cookie-less state — and asserts the codes: 401 dsh reachable
+ login wall holds, 403 evil origin fenced, 200 portal login, 302 `/open`
hides the token. It also asserts both phone traps on record: tailnet portal
must be 200-not-502 (2026-10-18 silent-death incident: all four processes
gone with zero log traces, backend dead, phone showed 502), and bare-IP on
`:9444` must fail TLS (expected: tailscale serve only speaks the MagicDNS
name there — the `ERR_SSL_PROTOCOL_ERROR` trap). Run it after every
`bin/start.sh` and before telling the user to reload.

## Programmatic read/write (actions visible in the app)

Yes — verified live 2026-10-18. Reads: sessions are zstd JSONL at
`~/.dsh/sessions/<workspace>/<session-id>/session.v4.jsonl` plus the
`~/.dsh/storages/session_projcache` index (titles, `sessionListMetadata`).
Writes: `dsh headless` runs headless-profile sessions that stay **invisible**
in the sidebar (no `sessionListMetadata` row — the list only shows
`blank: false` sessions). The visible path is `bin/act.mjs`: it drives the
real UI (New Session → type → Send → wait → chat tail), so the run
appears exactly as if the user typed it. Notes: Enter only newlines in
the prompt box — submission needs the Send button; fast runs (~2s) never
show a catchable Stop button, so completion is detected by chat content
settling, not by the Stop button.

## Phone-error inbox (nobody retypes errors)

Every portal page beacons failures to `POST /wk/client-error` (pre-login,
throttled 10/10min per IP): WebAuthn login/register/add-key crashes, page
errors, and the register-without-invite screen. Each error carries a
`derr_xxx` ref that is shown on the page itself — "ref #derr_x, sent
automatically, no need to report it" — and logged with timestamp, flow,
error, user-agent and IP. Operator rule: at every turn touching this
experiment, read `log/client-errors.log` past `log/.client-errors.cursor`,
advance the cursor, and surface each new entry as `[dsh-error #id]`.
There is no push channel into the agent session by platform design; the
inbox + ref IDs are the mechanism (verified: no session-messaging API
in the pi docs or CLI). E2E P0 covers it: guidance shown, beacon
landed, endpoint logs the ref.

`bin/e2e.mjs` goes all the way: headless Chrome at a phone viewport with a
virtual passkey authenticator clicks through the whole portal (login wrong/
right password, register admin, passkey login, password-change matrix, invite
create/consume, second-device enroll + remove, admin delete, logout leaks)
against an isolated throwaway portal, then drives the live dsh (token
exchange, 19-element inventory, 10-view tour, type-and-clear every input,
open session → Chat/Trajectory → New terminal → real `echo` rendered,
API gate, console-error watch). 20/20 green on 2026-10-18. What it caught:

- **Real portal bug (fixed):** enrolling a second device crashed the page
  (`regname` is null on the account page) — the exact flow a new phone
  needs. Plus human error text for `NotAllowedError` (was: raw browser
  jargon, the red text the user screenshotted).
- **Real upstream dsh bug (reported, not ours):** right-sidebar "New tab"
  with no session mounted throws Uncaught
  `sidebarRight: no session surface is mounted` instead of a no-op. The
  app survives it. Normal flow (open a session first) never hits it.
  Re-check after each dsh update; D7 tracks its exact signature.

## Session trail

Recorded 2026-08-15. See `e000-fundamentals/trail.md` for the session history.
