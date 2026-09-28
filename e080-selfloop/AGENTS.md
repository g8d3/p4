# e080 — Selfloop (the app that develops itself)

Web app that develops itself, ships new versions of itself, and answers
about itself so the user never has to ask.

## Product

| Surface | User action |
|---|---|
| Board `/` | ONE page. See Past / Present / Future, Why / What / How, and Self-questions with live answers. Start/finish next cycle, add goal, log usage, force re-ask. No login. |

Rule: one running cycle max. `finish` always bumps `version.json` (vN → vN+1).
The loop never stops: `bin/loop.sh daemon` asks the canonical questions,
answers them, ships a version, repeats. Stuck detection auto-fixes.

## Architecture

```
server/app.py    stdlib only: static public/ + /api/*
public/index.html  single-file UI, mobile-first, 10s refresh, zero deps
needs.json       ALL machine values (port, bind, budget, models, thresholds)
version.json     current version (bumped ONLY by finish)
data/cycles.jsonl   append-only cycle log (past)
data/goals.jsonl    future queue
data/usage.jsonl    AI token/credit ledger (present means)
data/answers.json   latest self-answers | answers.jsonl history
data/fixes.jsonl    stuck detections + fixes
data/heartbeat.json last loop heartbeat
bin/serve.sh     start/stop + live URL report (LAN/tailnet resolved live)
bin/loop.sh      one | daemon — one full self-pass: heartbeat → ask → unstuck → ship
test/check.sh    API + first-paint smoke
```

## Canonical self-questions (asked continuously, answered on the page)

1. Is the app working? → server alive + heartbeat age
2. Is development stuck? → running-cycle age + version age → auto-fix + log
3. How many tokens is the app using? → sum usage.jsonl
4. How many credits used since <date>? → filtered sum (default last 30d)
5. How many credits are left? → budget − used
6. Which endpoints and models? → distinct list from ledger + defaults
7. Is the UI as simple as it could be? → bytes / sections / actions grade
8. What is past / present / future? → cycles / version+health / goals
9. Why / What / How? → from needs.json (editable via goals, not code)
10. What ships next? → top open goal

## The continuous loop (each pass)

1. `heartbeat` → `ask` (re-answer all questions) → read `/api/health`.
2. If `stuck`: fix the cause (finish stale cycle) AND the fact (log fix, start smallest goal). Visible in Future + Fixes.
3. If no running cycle: start top goal. Do the smallest work that earns a bump (notes + changelog line).
4. `finish` → version bumps → visible on board. Exit / sleep / repeat.

## Run

```bash
bash bin/serve.sh            # start + URL report
bash bin/loop.sh one         # one self-pass (heartbeat+ask+unstuck+ship)
bash bin/loop.sh daemon      # never stops (polls every 60s, PID in data/loop.pid)
bash test/check.sh
```

## DONE ladder

1. WORKING — :8340 serves board, ask→answers, start→finish bumps v1→v2, check.sh PASS.
2. DEPLOYED — tailnet URL, loop daemon alive, survives reboot.
3. TESTED — stuck detected + auto-fixed, usage math correct.
4. ANNOUNCED — owner ping with URL.
5. MONETIZED — only after usage proof; budget tracked in needs.json.
