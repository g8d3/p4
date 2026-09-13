# e063 — Fleet UI v2 (better board for the e062 nervous system)

e062 proved the backend: `ops.db` + runner legs + proposals + beats.
Its board works but grew complex (1300-line `app.js`, per-widget query
language, full re-render jank, 60s silent poll). This experiment keeps
every e062 idea and re-skins it as an inbox-zero UI the owner can drive
from his phone in <30s.

## Ideas kept from e062 (not reinvented)

- `ops.db` is the truth (same file, read + same write SQL). No migration.
- `OWNER_SENTENCE | tech: detail` reporting + `report` pref simple/both/tech.
- Waiting = notes + pending gates, one badge, thumb-reachable.
- Run carries typed drafts (never drop owner words). Pause/resume per track.
- Rung ladder 1–5, treasury $300, auth = app accounts (same `users` table,
  so login works on both boards; passkeys stay on :8322, session cookie shared).
- Mobile hard rules: thumb zone, cards contain tables, 1-line + expand,
  sticky headers, inner scroll only.

## What is better

- 4 fixed views, default **Waiting** (inbox zero). No widget builder, no
  mini query language — one global search + status filter.
- One SSE stream (`/api/stream`) with a LIVE badge, not a silent 60s poll.
- Patch render that preserves focus/scroll/typed drafts (no "unclickable" refresh).
- Money gates as big approve/reject cards, not tiny table buttons.
- Single `app.js` (~450 lines) + `style.css` tokens, dark/light + density +
  font prefs shared with e062 (same `prefs` keys).

## Run

```
python3 app.py            # :8325, https with tailnet cert if present
curl -sk https://127.0.0.1:8325/api/state | head -c 300
```

## DONE ladder

1. WORKING — this file + app.py + static/* run on :8325, curl-verified.
2. DEPLOYED — tailnet URL, survives reboot (cron heartbeat reuse e062).
3. TESTED — `tests/check.sh` (API + no-console-error smoke).
4. ANNOUNCED — owner ping with URL + what it proves vs :8322.
5. MONETIZED — never (internal tool).
