# e069 — X Multisession (multi-account X library + Web UI)

Generalizes e064 (single-account @novaisabuilder pipe) into a
multi-account library + Web UI with pluggable undetectable-browser
backends. One registry, N accounts, each pinned to its own persistent
profile + browser backend.

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, browser discipline, quiet mode
- [../e020-undetectable-browser-benchmark/AGENTS.md](../e020-undetectable-browser-benchmark/AGENTS.md) — stealth ladder, CDP realities, **never copy cookies across fingerprints**
- [../e064-x-bookmarks/AGENTS.md](../e064-x-bookmarks/AGENTS.md) — X pipe contract (`latest.json` shape, login rule, freshness proof)
- [../e041-web-access-agents/AGENTS.md](../e041-web-access-agents/AGENTS.md) — vault login recipe
- Browser discipline: `browser-extract` skill — block image/media/font, `close --all`, 0 chrome processes at end.

## Layout
- `lib/xlib/` — the library (accounts, browsers, auth, extract, search, store)
- `ui/app.py` — FastAPI Web UI (account cards + sync/search buttons + results table)
- `docs/LOGIN.md` — user-assisted login runbook (password vs Google OAuth)
- `data/` — ignored, per-account raw cache (`data/<account_id>/...`)
- `profiles/` — ignored, one persistent `--user-data-dir` per account (NEVER committed)
- `output/` — per-account `latest.json` + global `accounts_state.json`

## Account model
```json
{ "id": "owner", "handle": "@novaisabuilder", "backend": "chrome|undetected|camoufox",
  "profile": "profiles/owner", "status": "ok|expired|blocked|never" }
```
Rules:
- One profile dir per account, forever pinned. Never clone a profile dir
  into a different backend (fingerprint mismatch reads as session theft).
- `accounts.json` holds id/handle/backend/profile only. No passwords, no tokens.

## Backend matrix (from e020)

| backend | driver | CDP tooling | use when |
|---------|--------|-------------|----------|
| `chrome` | `agent-browser open --profile` + L1 stealth | full (snapshot/network/eval) | default, non-adversarial |
| `undetected` | undetected-chromedriver + `--remote-debugging-port` + `agent-browser connect` | full via connect | X challenge / suspicious-login pages |
| `camoufox` | Playwright (`test-camoufox.sh` pattern) | partial (snapshot ok, network unreliable) | fingerprint matters more than interception |

Per-account backend switch = close session, relaunch with new backend,
re-verify login. One live browser per account max.

## Priority API (v1)
- `sessions.login_status(account)` → ok|expired|blocked (+handle check via snapshot)
- `sessions.logout(account)` → clear X session, keep profile dir
- `extract.likes(account, since_id)` / `extract.bookmarks(account, since_id)`
- `search.query(account, q, count)` → list of tweet dicts
- All extract/search go through the account's live session (ambient authority).
  Never replay captured headers via curl (401 trap — see browser-extract skill).

## DONE ladder
1. WORKING — 1 account live: login_status ok + likes/bookmarks/search return real rows.
2. MULTI — 2nd account on a different backend, both green at once.
3. DEPLOYED — UI on fixed port, `output/accounts_state.json` fresh.
4. TESTED — forced-logout → re-login drill per backend, documented.
5. ANNOUNCED — owner ping with counts.
