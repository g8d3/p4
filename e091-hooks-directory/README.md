# Hooks Directory

12 hook projects across 7+ chains, sourced live from X via twitterapis.com.

- Run: `bin/serve.sh`, open `/` (port in `needs.json`)
- API: `/api/hooks`, `/api/evidence`, `/api/health`
- Refresh: `TWITTERAPIS_API_KEY=... bin/fetch.sh`, then update `data/hooks.json`

See `AGENTS.md` for source queries and caveats.
