# e100-openbot

Test OpenBot (local-first multi-agent desktop app) wired to our default AI credentials.

- Default AI credentials: env vars starting with `OPENCODE` (see root `AGENTS.md`; names only, never values).
- Wiring: OpenBot provider type "OpenAI-compatible endpoint" -> base URL from `OPENCODE_GO_BASE_URL`, API key from `OPENCODE_GO_API_KEY`, model from `OPENCODE_GO_MODEL`.
- Never paste key values into files. Reference by env name only.
