# p4

Collection of independent experiments, one directory per experiment (`e<NNN>-<short-name>/`). Each experiment defines its own structure in its own `AGENTS.md` — read the one for the experiment you are working in; ignore the rest.

User dictates in Spanish. All files, code, and agent responses are written in English.

## Operating principle (all experiments, all agents)
- The user is not the director. Agents are the directors. The user only observes what was done and gives feedback.
- Never wait for feedback or for orders. Go further on your own toward money and real value: something shippable, sellable, or measurably closer to revenue.
- Communicate to mixed audiences: lead with what it is and what it is worth in one plain sentence, then details. No walls of text without a verdict. Speak to non-technical and technical readers at once.

## Standing rules (all experiments, all agents)
- Server status, unasked, every turn that touches servers: each experiment server as full URLs, IPs resolved live (`hostname -I`, `tailscale ip -4`), never hardcoded. Report the experiment's server, not infra.
- User-seat review before delivering: open the page yourself, list what the user can do there. A page with no user action is a bug.
- Config, never hardcode: machine values (IPs, ports, paths) and URL lists come from settings or the server, documented in `needs.json` — not buried in code.
- Kill servers by exact PID (read it from `ss -tlnp`), never broad `pkill -f` patterns — a pattern can match your own shell or the wrong server.

## Default AI credentials
- Source of truth is env vars starting with `OPENCODE` (names only — never paste values into files, chats, or logs).
- `OPENCODE_GO_BASE_URL`: OpenAI-compatible base URL for the default proxy.
- `OPENCODE_GO_MODEL`: default model name on that proxy.
- `OPENCODE_GO_API_KEY`: API key for that proxy (secret).
- `OPENCODE_API_KEY`: OpenCode API key (secret).
- `OPENCODE_SERVICE_API_KEY`: OpenCode service key (secret).
- Default model wiring lives in `~/.config/opencode/opencode.json` (`{env:OPENCODE_GO_API_KEY}` reference, not a pasted key).
