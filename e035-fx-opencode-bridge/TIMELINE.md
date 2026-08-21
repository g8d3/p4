# Timeline — measured, not estimated

Wall: **2026-08-20 16:42 → 19:12 (-0500) = 2h30m**  
Active: ~1h in `~/.local/bin/*`, rest waiting on `opencode.ai` + docs.

Evidence: `stat --time-style=full-iso`, `date -d @<epoch>`, `history`, `tmux window_activity`.

| Time (-0500) | Source | What happened |
|---|---|---|
| 16:42:19 | `zsh_history:1787262139` | first `fx` after `curl https://fx.sh/setup.sh` |
| 16:45:06 | `history:1787262306` | `fx` binary birth `16:45:40.088` (`12M`, `fx:3418` later) |
| 16:45:36 | `history:1787262336` | second `fx` install check |
| 16:59:55.984 | `stat fx-opencode-proxy.py birth` | created proxy after finding `isLoopbackHttpUrl` in `src/gateway/client.zig:591` |
| 17:02:46.639 | `stat ~/.cache/fx-proxy.log birth` | first proxy run (logger) |
| 17:03:29.655 | `stat fx-wrapper.sh / fx.real` | wrapper `3418B` that maps `OPENCODE_GO_*` → `FX_*` |
| 17:03:50.440 | `stat ~/.zshrc modify` | added wrapper note (removed shell function later) |
| 17:12:06.221 | `stat fx-opencode-proxy.py modify` | last proxy fix (`User-Agent: fx/0.0.4` + `finish_emitted`) |
| 18:58:26 | `history:1787270306` | `python3 proxy` in `main:1` (misread — proxy, not fx) |
| 19:00:10 | `history:1787270410` | `kill 33171`, `nohup` proxy `33716`, `fx` in `main:1` (`auto · muse-spark-1.2-contributor`) |
| 19:06:45.854 | `stat AGENTS.md birth` | wrote `e035` docs |
| 19:12:18 | `tmux window_activity 1787271138` | final capture `main:1` |

## Breakdown

- **0:00–0:12 (12m)**: proxy skeleton, found loopback check via `strings fx` + `raw.githubusercontent`.
- **0:12–0:27 (15m)**: wrapper `fx` → `fx.real` install, `ss -tln | grep 8765` loop.
- **0:27–1:30 (63m)**: debug loop — `403 code 1010` (Cloudflare blocks `Python-urllib`), `StreamInterrupted ×10` (OpenAI SSE vs Vercel `text-delta`/`finish`), `400` empty `tool_call_id` → `user` fallback.
- **1:30–2:30 (60m)**: tmux confusion + docs (`THREAD.md`, `README.md`).

## How to re-verify

```bash
ls -l --time-style=full-iso ~/.local/bin/fx* | head
stat ~/.cache/fx-proxy.log
date -d @1787262306 --iso-8601=seconds
tmux list-windows -t main -F "#{window_index} #{window_name} #{window_activity}"
tail -n 20 ~/.zsh_history | grep fx
```
