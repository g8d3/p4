# e093 — Rakazo (source checkout)

Local source checkout of https://github.com/elie222/rakazo.git at `rakazo/` (nested clone, own upstream remote; p4 ignores it, never commit here — commit upstream in `rakazo/` only if needed).

Setup path: source checkout (pnpm), web only, `SANDBOX_PROVIDER=docker`, no managed catalog, model via deployment-wide `OPENROUTER_API_KEY` (user adds key into `rakazo/.env`; never echo/print it).

## Layout

- `rakazo/` — upstream checkout (commit 50fa0321 at setup; ignored by p4). All app code, `.env` (generated 2026-10-12, secrets via openssl), `data/` live here.
- `needs.json` — machine values (ports/bind/paths); code reads this, never hardcode.
- Postgres: Compose service `postgres` (volume `compose_pgdata`), host overlay publishes `127.0.0.1:5433` only when host-side DB access needed (`db:migrate`, GUI tools). Base file keeps Postgres network-internal.

## Run

```bash
cd rakazo
docker compose --env-file .env -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.postgres-host.yml up postgres -d
npx --yes pnpm@9.15.0 install --frozen-lockfile
npx --yes pnpm@9.15.0 db:generate
npx --yes pnpm@9.15.0 db:migrate
npx --yes pnpm@9.15.0 sandbox:build   # docker build -t rakazo/computer:local (slow, desktop+Chromium)
npx --yes pnpm@9.15.0 dev             # api+worker+web+sandbox-supervisor, keep running
```

Health: `http://127.0.0.1:3100/health` requires `ok:true runtime:pi sandbox:docker jobs:graphile realtime:postgres`.
App (remote, HTTPS): `https://vuos-hcar5000mi.tail6918b0.ts.net` — primary URL, WEB_ORIGIN set to it. Served by `tailscale serve --bg --https=443 http://127.0.0.1:5173` (tailnet only). The old `http://100.102.52.59:5173` and the LAN IP still load the UI but auth rejects their origin (INVALID_ORIGIN) — plain HTTP on a non-loopback host is not a secure context, so browser dictation/mic cannot work there.
App (loopback): `http://127.0.0.1:5173` — trusted auth origin (BETTER_AUTH_URL).
App (LAN `http://192.168.0.177:5173`): UI loads, auth rejects origin (INVALID_ORIGIN) by design — use the tailscale URL.
Supervisor: `http://127.0.0.1:7091` (loopback only).

## Remote access (2026-10-12)

- Vite dev `server.host` reads `RAKAZO_DEV_HOST` (local diff in `apps/web/vite.config.ts`, default
  `127.0.0.1`, `.env` sets `0.0.0.0`). One-line local-only change; not committed upstream.
- `.env`: `WEB_ORIGIN=https://vuos-hcar5000mi.tail6918b0.ts.net` (origin policy: WEB_ORIGIN + BETTER_AUTH_URL are
  the two browser origins better-auth trusts; API loopback stays unexposed, browser only ever
  talks to :5173 via the Vite proxy).
- HTTPS ingress (2026-10-12): Tailscale Serve on 443 -> `127.0.0.1:5173`, plus `RAKAZO_HOST` and a Vite `server.allowedHosts` addition (see needs.json local_diff). Backups: `.env.bak-2026-10-12-https`, `apps/web/vite.config.ts.bak-2026-10-12-https`.

## Rules

- Never overwrite `rakazo/.env`; inspect key presence only, never print values.
- Never print/log/commit secrets. `.env` is ignored in both repos.
- Kill servers by exact PID from `ss -tlnp`, never broad pkill.
- Normal stop without deleting data: `docker compose ... down` WITHOUT `-v`. Never use `pnpm compose:down` for a normal stop (it includes `-v` and wipes pgdata).
- OPENROUTER_API_KEY: user enters directly into `rakazo/.env`; agent never echoes it back.
