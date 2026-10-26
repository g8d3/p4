# X API findings (read-only check)

*Sun 2026-10-25 10:45 Bogotá*

- Posting script: `~/code/p4/e092-echolike/publicar_x.py` — POST `https://api.x.com/2/tweets` via OAuth1 (`requests_oauthlib.OAuth1`), 30s timeout. Guards: ≤280 chars, no `$cashtags`, no URLs. `--dry` prints without posting; `--delete <id>` deletes.
- Reader: `~/code/p4/e092-echolike/x_lectura.py` — read-only likes/bookmarks, GET only, cost caps (`X_TOPE_MES` default $2/mo).
- Account: @novaisabuilder ("Nova Radar", id 2018710788995792896) — confirmed live via GET /2/users/me, status 200. Handle default `X_USERNAME=novaisabuilder` in `x_lectura.py`; also listed in `e092-echolike/AGENTS.md` credentials section.
- Creds location (names only, never values): `~/code/p4/e092-echolike/.secrets/x_api.env` with `X_CONSUMER_KEY`, `X_CONSUMER_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` (OAuth1 posting), plus `X_BEARER`, `X_CLIENT_ID`, `X_CLIENT_SECRET`, `X_OAUTH2`, `X_USER_ID`, `X_USERNAME`. Supplements: `X_TOPE_MES`, `X_MAX_RESULTS`, `X_LECTURA_CADA`.
- Read-only check: PASSED. `GET https://api.x.com/2/users/me` → 200, username novaisabuilder. Nothing posted, liked, replied, or DM'd.
- Command to post one tweet later (needs Nova's explicit OK each time; dry-run first):

```
python3 ~/code/p4/e092-echolike/publicar_x.py --dry "draft text here"
python3 ~/code/p4/e092-echolike/publicar_x.py "final text here"
```
