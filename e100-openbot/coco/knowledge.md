# Coco — knowledge notes (facts as of Oct 24, 2026, Bogotá)

## Mini PC
- Repo `~/code/p4`: one folder per experiment (`eNNN-name/`), each with its own AGENTS.md. Read `~/code/p4/AGENTS.md` first.
- Wi-Fi card rtw_8821ce: power-saving disabled via `/etc/modprobe.d` (`disable_lps_deep=Y`, `disable_aspm=Y`).
- Overheating history: most echolike-* services are disabled on purpose. Leave them off.
- AI env vars (names only): `OPENCODE_GO_BASE_URL`, `OPENCODE_GO_MODEL`, `OPENCODE_GO_API_KEY`, `ZAI_API_KEY`.
- Cloudflare env vars: `CLOUDFLARE_FOCALIS_API_KEY` (account token), `CLOUDFLARE_ACCOUNT_ID`.

## Email (send and receive, no Grok Bot dependency)
- hello@ and founders@echolike.app: DNS at Porkbun, MX = Forward Email. Forwarded to a webhook on https://focalis.cc/<token> (Cloudflare tunnel -> localhost:80) -> `correo-receptor.service` -> saved in `~/code/p4/e092-echolike/correo/inbox/` (gitignored). Also copied to a backup inbox.
- hello@focalis.cc: DNS at Cloudflare; Email Routing -> Worker `focalis-correo` -> mini PC receiver + Nova's Gmail. hola@ and contact@focalis.cc go to Gmail only.
- Sending: `python3 ~/code/p4/e092-echolike/correo/send.py` (Resend; both domains verified; key lives in `.secrets/`, gitignored). Sending to anyone other than Nova needs his OK.
- Details: `~/code/p4/e092-echolike/correo/README.md`.

## Hummingbot paper pilot (e101)
- `~/code/p4/e101-hummingbot`: Docker container `e101-hummingbot` paper-trading ETH-USDT; `e101-liquidity-publish.timer` (user unit) publishes status hourly to the landing page https://g8d3.github.io/echolike-site/liquidity/.
- Stop: `cd ~/code/p4/e101-hummingbot && docker compose down && systemctl --user disable --now e101-liquidity-publish.timer`.
- Status: pilot only, no fills yet; landing page judged NOT ready to sell. Outreach drafts in `outreach_drafts.md` are unsent.

## OpenBot (e100)
- AppImage on DISPLAY=:99, launched by `bin/launch.sh` (dedicated unlocked keyring), controlled over CDP port 9222 (`obctl.py`, `bin/*.py`). Signed in as hello@echolike.app. See `notes.md`.
