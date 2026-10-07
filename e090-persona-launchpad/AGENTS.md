# e090 — Persona Launchpad (AI-persona factory + social testbed + Clanker funds path)

Target from user (2026-10-07): platform where AI-created persons are tested on
socials to find what sticks; mix humor + social causes; start with TWO niches;
eventually self-serve so anyone can create a persona easily. Full Claus-style
clone (X persona + public logs + token via Clanker v4 on Base), hosted locally.

## System

- `server/app.py` — stdlib only. Serves `public/`, JSON API:
  `GET /api/personas`, `GET /api/logs`, `POST /api/personas` (create),
  `POST /api/log` (append public log), `GET /api/funds` (how Klaus/Clanker money works).
- `public/index.html` — single file UI with 3 tabs: Personas (factory + scores),
  Public Logs (transparency feed, Claus-style), Funds (how locked LP + fees work).
- `data/personas.json` — persona defs. `data/logs.jsonl` — public log feed.
- `bin/serve.sh` / `bin/worker.sh` — serve + one content-generation pass.
- `needs.json` — bind, port, chain, launcher, flags. Secrets NEVER in repo;
  when X/wallet arrive they go in `data/secrets.env` (chmod 600, gitignored).

## Rules

- Ponytail discipline: stdlib + CDN only, smallest shippable step.
- No ask_user (per e088 correction): decide, build, log.
- Seed niches (decided): A = common-good comedy, B = animal street-hero.
- Token launches are real-money actions: DRY-RUN only until user pastes
  WALLET_ADDRESS + funds Base ETH and confirms in UI checklist.
- Standing rules apply: live IPs/URLs, user-seat review, config from
  needs.json, kill by exact PID from `ss -tlnp`.

## Roadmap

1. v0 (this cut): factory UI + scoring + public logs + funds explainer. No keys needed.
2. v1: X connector (API mode + free copy-paste mode), auto-post loop.
3. v2: Clanker v4 deploy (vault + static/dynamic fee hook + locked LP), fee claim to treasury.
4. v3: self-serve wizard (anyone creates a persona in 3 clicks).
