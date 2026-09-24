# e042-meet-send-1 — Strip PIN from overview, reboot, re-verify public URL, stage send (2026-09-24)

One-line fix in `e042-bk2/app.py` (committed as `92a4e5e`), app rebooted,
all checks re-run this leg. Every cell below comes from a command run on
2026-09-24 (`curl` local + public, `python3` JSON parse, `diff`, `git`,
process list) or stays empty. Secrets redacted: PIN and session token
values are never quoted here (lengths / ok-flags only).

## Verdict: PIN leak closed, public URL serves the PIN login, send staged

- Authed `/api/overview` no longer contains the PIN (`pin_present=False`);
  `/api/report` inherits the same clean settings (`pin_present=False`).
- Login still works (`login_ok=True`), Ajustes PIN-change path untouched.
- Public Funnel URL returns 200, byte-identical to local 9091 (both
  39491B), PIN login screen present, public `/api/report` unauth 401.
- Data intact through the reboot: 38 members / 76 credits in authed
  overview JSON (same counts as `e042-meet-prep-1.md` / `e042-funnel-fix-1.md`).
- Send: no messaging CLI exists on this box (scanned: signal-cli,
  whatsapp, sms, mail, sendmail, twilio — none present), so the live URL
  + share text is staged below for the owner to forward outside the repo
  (phone/WhatsApp). Open-confirm PENDING owner reply; meeting date not in
  repo (empty, not invented).

## Fix applied (e042-bk2, committed)

| step | method | result | checked_at |
|---|---|---|---|
| strip PIN from overview response | 1-line edit `app.py` `overview()`: return `{k:v ... if k != "pin"}`; `report()` inherits via `overview()` | `git diff`: 1 file, 1 insertion, 1 deletion | 2026-09-24 |
| commit | `git commit` in `e042-bk2` | `92a4e5e`, 7th commit, working tree clean | 2026-09-24 |
| reboot app | `pkill` uvicorn 9091, `nohup python3 -m uvicorn app:app --host 127.0.0.1 --port 9091` | log `Uvicorn running on http://127.0.0.1:9091`, local `/` 200 | 2026-09-24 |

## Verified this leg (after reboot)

| check | method | result | checked_at |
|---|---|---|---|
| PIN absent from overview JSON | authed `GET /api/overview`, parse `settings` keys | keys `diezmo_pct,rate_pct,solidaridad,term_distribucion,valor_inicial`, `pin_present=False` | 2026-09-24 |
| PIN absent from report JSON | authed `GET /api/report`, parse `settings` keys | same 5 keys, `pin_present=False` | 2026-09-24 |
| counts intact | authed overview JSON lengths | 38 members, 76 credits, `action_value` present | 2026-09-24 |
| login still gates | `POST /api/login` with stored PIN | `login_ok=True` | 2026-09-24 |
| unauth still blocked (local) | `GET /api/report` without cookie | 401 | 2026-09-24 |
| public root serves app | `curl` public Funnel URL | 200, 39491B | 2026-09-24 |
| public equals local | `diff` public body vs `http://127.0.0.1:9091/` body | identical | 2026-09-24 |
| PIN login screen (public) | `grep` public body | title Banco Comunal x3, password inputs x2 | 2026-09-24 |
| public gate holds | `curl` public `/api/report` without cookie | 401 | 2026-09-24 |
| funnel process live | `ps aux \| grep tailscale funnel` | process running (survived app reboot, proxy re-connected) | 2026-09-24 |

## Send (staged for owner, outside repo)

Live URL (already public in `e042-bk2/AGENTS.md`, not secret):

- `https://vuos-hcar5000mi.tail6918b0.ts.net/`

Share text (copy/paste to dad, PIN shared verbally — never written here):

- "Esta es la aplicación del Bancomunal para la reunión. Ábrela, ingresa el PIN que te di por llamada y confirma que ves el cuadro contable."

| item | status | checked_at |
|---|---|---|
| URL sent outside repo | STAGED — no send CLI on this box; owner forwards via phone/WhatsApp | 2026-09-24 |
| dad opened it (open-confirm) | PENDING owner reply | empty |
| bank meeting date | not in repo | empty |

## Notes (honest, not blockers for the meeting)

- Data gaps from `e042-meet-prep-1.md` stand (0 valorizations, preview
  income 0.0, negative box): data work for after the call connects.
- After any machine reboot: restart uvicorn 9091, re-run `./funnel.sh` in
  `e042-bk2`, re-check the public URL before the meeting.

## Evidence ledger (command → fact, no invented numbers)

- `curl --cookie bk_session=<redacted> /api/overview | python3 parse` → settings 5 keys, `pin_present=False`, 38 members, 76 credits.
- `curl --cookie bk_session=<redacted> /api/report | python3 parse` → settings 5 keys, `pin_present=False`.
- `curl /api/report` (no cookie) → 401 local and 401 public.
- `curl -X POST /api/login` with stored PIN → `{"ok":true}` (value redacted, flag only).
- Public `/` → 200 39491B; local `/` → 200 39491B; `diff` → identical.
- `grep` public body → Banco Comunal x3, password inputs x2.
- `git diff --stat` → `app.py | 2 +- 1 insertion, 1 deletion`; `git log` → `92a4e5e` on top.
