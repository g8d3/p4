# p4

Collection of independent experiments, one directory per experiment (`e<NNN>-<short-name>/`). Each experiment defines its own structure in its own `AGENTS.md` — read the one for the experiment you are working in; ignore the rest.

User dictates in Spanish. All files, code, and agent responses are written in English.

## Standing rules (all experiments, all agents)
- Server status, unasked, every turn that touches servers: each experiment server as full URLs, IPs resolved live (`hostname -I`, `tailscale ip -4`), never hardcoded. Report the experiment's server, not infra.
- User-seat review before delivering: open the page yourself, list what the user can do there. A page with no user action is a bug.
- Config, never hardcode: machine values (IPs, ports, paths) and URL lists come from settings or the server, documented in `needs.json` — not buried in code.
