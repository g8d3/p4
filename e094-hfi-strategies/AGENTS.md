# e094 — HFI Strategy Map (HawkFi 19 strategies, visual explainer)

Single page. Interactive 2D map + 5 looping market-scene animations + 2-question
recommender. Zero deps, single-file UI, stdlib-only server.

## Product

| Surface | User action |
|---|---|
| Map `/` | Hover/click any of 19 dots → detail card + which scene to watch; family filter chips; regime × width axes. |
| Hero animation | Pick scene (chop / volatile / trend / oscillation / crash) + pick shape inside it → price loop plays, fees tick when green, grey = out of range dead. Play/pause, speed. |
| Recommender | Two dropdowns (where is price going? how long stay?) → 2–3 recommended strategies, click jumps to map + hero. |
| Grid | All 19 cards, click loads into hero. |

## Architecture

```
server/app.py   stdlib only (threaded) + /api/health + /api/needs
public/index.html  single-file UI, zero deps, 6 canvases (1 hero + 5 minis)
needs.json      port/host/paths (code reads this, never hardcode)
bin/run.sh      start server on needs.json port
```

## Run

```bash
bash bin/run.sh            # server on port from needs.json
curl -s localhost:<port>/api/health
```
