# e107 — dsh-superagent prototype (play + verdict)

Upstream: https://github.com/deepseek-ai/dsh-superagent-prototype @ `6337fc8`
Local copy: `upstream/` (gitignored vendor dir — run `bin/fetch.sh` to clone the pinned commit).

## What it is

DeepSeek's research prototype of a **proactive coding agent for one GitHub repo**,
packaged as a DSH (DeepSeek Harness) bundle. Listens to GitHub (+ optional Feishu),
evaluates requests under a Policy, turns authorized ones into Tickets, executes each
in its own DSH Session + directory, answers back as PR/comment. Panel shows only
what needs a person. Philosophy: *take as little human attention as possible.*

## Verdict (one line)

Well-designed attention-minimal agent framework; directly reusable as the
execution/policy core for our agent-company work — worth a deeper integration spike.

## What was done here

- `pnpm install` — clean, ~13 s, all deps resolve.
- `pnpm typecheck` — passes.
- `pnpm build` (tsdown) — passes, ~6 s, 11 files / 693 KB.
- `pnpm test` (vitest) — **1196/1197 pass**. One genuine failure:
  `tests/sources.spec.ts > feishu event consumer > takes in the event lines it reads…`
  expects a malformed `not json` event line to flip `health.feishu` to
  `{state:'error', detail: /JSON/}`, but health stays `{state:'ready'}`.
  Consistent (suite + isolated re-run). Single-commit repo, so the bug ships
  in the published prototype. See `PLAY.md`.
- Docs read in order: 000-philosophy, 001-domain, 002-authorization,
  003-execution, 005-panel, 006-deployment, 007-architecture, 008-cookbook.

## Reproduce

```sh
bin/fetch.sh && cd upstream && pnpm install && pnpm typecheck && pnpm build
pnpm test                                   # 1 known failure above
pnpm vitest run tests/sources.spec.ts -t "malformed line"
```

Toolchain: node 24, pnpm 11.7.0 (via corepack), no `dsh` binary needed for the above.

## Live panel (running)

You don't need localhost. The panel is served through the tailnet with a trusted cert:

- **Portal (your entry): https://vuos-hcar5000mi.tail6918b0.ts.net:9446** — log in with the portal password/passkey, press **Open superagent**. The portal reads the per-boot dsh token live; the token itself is never pasted anywhere.
- Direct (needs the token URL from `log/superagent.log`): `https://vuos-hcar5000mi.tail6918b0.ts.net:9445/`.
- Use the MagicDNS hostname URL, not a bare IP — passkeys only work there (rpId rule, see e028).
- Expect a setup checklist in Overview (no GitHub agent account configured yet) — that is the operator-steps stage of upstream SETUP.md, not a malfunction.
- Stack: dsh `--profile superagent` on 127.0.0.1:3082 → socat TLS :8444 → `tailscale serve :9445`; portal :8091 → `tailscale serve :9446`. PIDs in `log/*.pid`; `bin/start.sh` / `bin/stop.sh` (exact-PID kills). dsh 0.2.1-rc.2 from e028/app; bundle linked from `upstream/` (gitignored, fetch with `bin/fetch.sh`).

## Rules

- Standing rules apply (server URLs, user-seat review, needs.json, PID kills, push by default).
- No server in this experiment yet (no `dsh` binary installed, no agent GitHub account created).
- Next step if pursued: install `dsh@0.2.1-rc.3`, create `superagent` profile, run a live
  Ticket against a scratch repo with a dedicated agent account (see upstream SETUP.md +
  docs/006-deployment.md). Do NOT use the owner's GitHub account as the agent.

## Roadmap

1. This cut: play + verdict + bug report (done).
2. Live spike: dsh + superagent profile + scratch repo, one `@agent` mention → Ticket → PR.
3. Reuse decision: port Policy/Eval/Ticket attention rules into our agent-company stack.
