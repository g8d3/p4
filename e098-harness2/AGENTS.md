# e098 — Harness² (Google Research recursive agent harnessing)

Tried Google's Harness² locally: agents that rewrite their own harness
(system prompt, guardrails, memory, tool guidance, subagents, skills, scripts,
plugins) via Propose–Probe–Compose, keeping lessons across tasks. The
no-credential local demo passes end-to-end on this machine ($0, real executions).

## Product

Server binds `0.0.0.0` (all interfaces). Note: the re-run form executes
`bin/demo.sh` on this machine — anyone with network access to the port can
trigger a demo run (fixed command, k clamped 1–4, ~10s, $0).

| Surface | User action |
|---|---|
| Results page (port in `needs.json`) | Read what Harness² is and what the demo proved; re-run the demo with a new recursion budget `k` via the form (POST `/api/rerun?k=N`); follow links to repo/paper; copy benchmark commands for a model-backed run. |
| `bin/demo.sh [k]` | Re-run the local demo (default k=2), re-render the site. |
| `bin/serve.sh` / `bin/stop.sh` | Start/stop the results server. PID comes from `ss -tlnp`, kill by exact PID. |
| `upstream/` | Pinned git clone of `google-research/harness2` + its `.venv`. Untouched upstream code; our wrapper lives in `bin/`, `site/`. |

## Architecture

```
needs.json     machine values (port, paths) — scripts read this, never hardcoded
bin/render.py  stdlib: parses upstream/runs/demo → site/index.html
bin/server.py  stdlib ThreadingHTTPServer: static files + POST /api/rerun
bin/demo.sh    harness2-demo --output <demo_output> --k <k> + render
upstream/      google-research/harness2 @ 1cfe254, .venv (py3.12, .[render])
site/          generated static page (regenerated on every demo/serve)
```

Demo mechanics (from `upstream/harness2/demo.py`): base harness script sums only
positive ledger amounts (bug: drops credits). Task-level recursion proposes
removing the filter, probes base vs candidate on the same ledger, composes the
fix from the behavioral contrast. Harnessing-level recursion stores the lesson
in `library/k2/.../EXPERIENCE.md`, reused on the second task.

## Run

```bash
bin/demo.sh 2        # local demo, no credentials, ~10s
bin/serve.sh         # render + serve results page, prints HTTP status
bin/stop.sh          # stop by exact PID
```

Model-backed benchmarks (JobBench / LAB / WorkBuddy-Bench) need Vertex AI:
`gcloud`, `GOOGLE_CLOUD_PROJECT`, `HARNESS2_SOLVER_MODEL` etc. Not configured
here — this machine has `GEMINI_API_KEY` (AI Studio), Harness² requires Vertex
Application Default Credentials. That is the explicit next step with a cost
warning: real runs bill per task (R=4k rollouts, P=3k improver sessions).

## Rules

- Never commit `upstream/.venv/`, `upstream/runs/`, `upstream/dependencies/`, `site/.serve.pid`.
- No secrets in files; Vertex credentials stay in env/gcloud, never in repo.
- Servers: full URLs with live IPs (`hostname -I`, `tailscale ip -4`), never hardcoded ports outside `needs.json`.
