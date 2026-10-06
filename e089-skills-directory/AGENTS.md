# e089 — Skills Directory (AI-agent skills, web-dev first, signals over stars)

Goal: a web directory of AI-agent skills where every listing earns its rank
with numbers — installs velocity, repo freshness, independent mentions —
never raw GitHub stars alone.

## Structure

- `needs.json` — port/bind/refresh; only machine values file.
- `server/app.py` — stdlib only. Serves `/`, `/v2`–`/v13`, `/api/skills`,
  `/api/health`. Version routes are regex-generalized; no per-version code.
- `public/index.html` — v1 baseline (no skill): search, category filter, sort.
- `public/v2.html`–`public/v13.html` — one redesign per directory skill,
  strictly score-ordered: v2 frontend-design (98), v3 superpowers (90),
  v4 playwright-skill as webapp-testing stand-in (84),
  v5 web-design-guidelines (82), v6 vercel-react-best-practices (81),
  v7 ui-ux-pro-max (80), v8 impeccable/pbakaus (79),
  v9 vercel-composition-patterns (78), v10 jeffallan collection (76),
  v11 alirezarezvani collection (74), v12 figma-implement-design (72),
  v13 ponytail (70). Each file self-contained (system fonts, zero external
  requests), all five actions (search, filter, sort, copy-install, source).
  Every page carries the same sticky bottom version bar (v1–v13).
  Skill-substitution caveats live in each file's leading HTML comment.
- `data/skills.json` — the listings. Fields per skill: name, repo,
  category, blurb, installs, trend8w, stars_repo, stars_note, last_commit,
  mentions, score, install_cmd, skill_url, verified.
- `bin/serve.sh` — start server (reads port from needs.json).

## Ranking rule (v1)

score = installs_velocity_weight + freshness + independent_mentions.
Raw stars NEVER rank. `stars_repo` shown only with `stars_note`
(e.g. "shared across whole repo — not skill-specific").

## Refresh loop

`data/skills.json` is seeded from live web research (2026-10-05, tinyfish).
Next legs: scrape skills.sh leaderboard + trending weekly, re-fetch GitHub
commit dates, append Reddit/YouTube mentions. Each refresh bumps `verified`.

## Inherits
- [../AGENTS.md](../AGENTS.md) — standing rules (live IPs, user-seat review,
  config from needs.json, kill by exact PID).
