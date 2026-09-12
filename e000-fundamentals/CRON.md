# Cron jobs that write into this repo

`crontab -l` on this machine holds entries for both p3 and p4. **Only these
touch p4** — anything a cron writes into the repo must be classified here
(tracked + auto-pushed, or explicitly ignored). Local time (America/Bogota).

| When | Command | Writes into p4 | Git | Auto-push |
|---|---|---|---|---|
| `15 0 * * *` | `e025-hyperliquid-candle-tails/ag-16-live-monitor/bin/paper_trade_cron.sh` | `ag-16-live-monitor/output/paper_state.json`, `output/paper_trades.csv` | **tracked** | yes (heartbeat) |
| `30 0 * * *` | `e040-traderdev-local-replica/bin/paper_tsmr_cron.sh` | `output/tsmr_paper_state.json` | **tracked** | yes (heartbeat) |
| `@reboot` (+`sleep 90`) ×2 | same two wrappers, catch-up if the PC was off at run time | same files | **tracked** | yes |
| `25 10 * * *` | `e057-launchpad-tokens/bin/refresh.sh` | `data/` (raw API cache), `output/` (report, `stats.csv`, charts, `site/`), `refresh.log` | **all ignored** | no — the published site lives in `e057-launchpad-tokens/repo/` (`g8d3/launchpad-radar`) and deploys by its own GitHub Actions cron |
| `*/15 * * * *` | `e058-funding-scanner/bin/sample.sh` | `data/` (funding snapshots), `data.db` (SQLite series), `sample.log` | **all ignored** | no |
| `*/30 * * * *` | `e062-agent-ops/bin/runner.sh` | `runner.log`, `ops.db` (bus state) | **all ignored** | no (dispatcher legs; see DIRECTIVES.md) |
| `@reboot` | `e000-fundamentals/bin/watch-agents.sh` | `~/.opencode/{agent-status.md,watch-agents.pid}` — **outside the repo** | n/a | n/a |

Everything else in the crontab belongs to p3 (`~/code/p3/s46/scheduler/*`) and
never writes here. The `systemd --user` timers (`filex-validate`) stay in
`~/code/filex`.

## Rule: every cron-written path is either tracked-with-autopush or explicitly ignored

- **Tracked + auto-pushed** — the file *is* the experiment's deliverable and
  a daily commit is the heartbeat (no commit on a date = the PC was off that
  day). The wrapper commits only inside its own experiment directory, so a
  scheduled job can never drag unrelated work into a commit.
- **Ignored** — regenerable/raw/heavy (API caches, logs, rendered charts,
  nested repos). `.gitignore` global rules already cover `*.log`, `output/`,
  `node_modules/`, `upstream/`, and media (`*.mp4`, `*.png` is *not* global).
  An experiment that relies on a global pattern should also drop a local
  `.gitignore` naming its paths, so the policy survives root-level edits.

`.gitignore` negation note: re-including a directory (`!e040-…/output/`) does
**not** re-include files matched by later global patterns such as `*.log`, so
state/CSV upload but logs never do.

## Adding a new cron that writes into p4

1. Write output under the experiment directory, never in the repo root.
2. Pick the bucket above and make it explicit: either add
   `git add -A -- <experiment>/<path>/` + `git commit` + `git push` to the
   wrapper (copy `e040-traderdev-local-replica/bin/paper_tsmr_cron.sh`), or add
   the path to `.gitignore`.
3. Add a row to the table above and a line to the experiment's `AGENTS.md`
   (what it writes, how to verify with `auto-push OK` in the log).

## Known caveat: `git add -A -- <exp>/output/`

The e025/e040 wrappers stage their **whole** `output/` directory, so any new
non-ignored file dropped there is committed and pushed by the next nightly
run. Keep raw downloads out of those directories — put them in `data/` and
ignore it (as e057 does). `e040-…/output/` already carries ~26 MB of committed
market CSVs as the experiment's dataset: read them, don't re-fetch into it.
