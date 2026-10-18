# Ops Rules — X Publishing for the Sales Pack

## 48-hour veto window

- Every sales or audit post (thread drafts, landing claims, numbers) sits in `posts_programados/` for a full 48 hours before the queue may publish it.
- Veto by Nova (owner) at any point in the window kills the post: move the file out of `posts_programados/`, log the veto, no re-queue without a new 48-hour clock.
- Emergency correction (wrong number, broken caveat): veto first, fix, restart the 48-hour clock. Speed never beats correctness.

## Kill switch

- Stop all scheduled publishing immediately with:

```
systemctl --user stop echolike-cola.timer
```

- This halts `echolike-cola.service` (the 15-min queue runner: `publicar_cola.py` via `publicar_x.py`). Already-published posts stay; nothing new goes out.
- After stopping, verify with `systemctl --user status echolike-cola.timer` and move pending sales files out of `posts_programados/`.
- Restart only by explicit owner order: `systemctl --user start echolike-cola.timer`.

## Caps — posts per day and API

- Sales threads: max 1 thread (max 6 posts) per day, min 60 minutes between posts in a thread.
- Whole account: max 8 posts per rolling 24 hours, including replies. Replies to customers come first; sales posts yield.
- X API: stay under 300 reads and 50 writes per 24 hours for this pack. One `--dry` validation per draft is free (no API call); live posts only via the queue.
- Validator is mandatory: every post must pass `.venv/bin/python publicar_x.py --dry` from `/home/vuos/code/p4/e092-echolike` (280 chars, no cashtags, no URLs) before it enters `posts_programados/`.
- Failed publishes land in `posts_fallidos/` — do not retry without owner review. Log the error, wait one queue cycle (15 min), then decide.

## Secrets and safety

- Keys live only in `.secrets/x_api.env` (chmod 600). Never print, never commit, never paste into drafts or logs.
- Validate with `--dry` only. Never test-post to production.
- Sales pack files stay in `/tmp/night/sales/` as files only. Nothing in this pack is published except through the queue after the veto window.
