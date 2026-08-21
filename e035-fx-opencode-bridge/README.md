# e035 — fx + opencode bridge

> Make `fx` respect `OPENCODE_GO_*` without forking Zig.

This experiment is the documentation for the bridge we built on 20 Aug 2026 (~2.5h). For the full human story and X thread, see `THREAD.md`. For agent contract, see `AGENTS.md`.

## TL;DR

- **Problem:** `fx` (Vercel, `0.0.4`) is hard-wired to `https://ai-gateway.vercel.sh`. Setting `FX_GATEWAY_BASE_URL=https://opencode.ai/zen/go/v1/` is silently ignored.
- **Solution:** `~/.local/bin/fx` wrapper + `http://127.0.0.1:8765` proxy that translates Vercel gateway ↔ OpenAI.
- **Result:** `fx status` shows `muse-spark-1.2-contributor` from `OPENCODE_GO_MODEL`, `fx ask` burns opencode credit.

## Files

- `AGENTS.md` — pain points, architecture, verification
- `THREAD.md` — X thread (8 tweets, human voice)
- This `README.md`

Actual code lives outside the experiment (so `fx` works globally):

- `~/.local/bin/fx` — wrapper (3418B)
- `~/.local/bin/fx.real` — original binary (12M)
- `~/.local/bin/fx-opencode-proxy.py` — translator (470 lines)
- `~/.cache/fx-proxy.log` — log
- `~/.config/systemd/user/fx-opencode-proxy.service` — optional daemon

## Quick start (new tmux window)

You don't need to configure anything. `OPENCODE_GO_*` are already in env (from `~/.hermes/.env`).

```bash
# fx is already patched globally. Just run it anywhere:
fx status
fx ask "what's in this repo?" --no-save

# New tmux window as you asked:
tmux new-window -n my-fx -d
tmux send-keys -t my-fx "fx" Enter
# or one-off:
tmux new-window -n tmp -d
tmux send-keys -t tmp "fx ask --yolo 'list files' --no-save" Enter

# Check proxy:
ss -tln | grep 8765
cat ~/.cache/fx-proxy.log | tail
ps -o pid,args | grep fx-opencode
```

If proxy dies (reboot):
```bash
nohup python3 ~/.local/bin/fx-opencode-proxy.py > ~/.cache/fx-proxy.log 2>&1 &
# or
systemctl --user enable --now fx-opencode-proxy
```

The wrapper auto-restarts it on next `fx` call anyway (`ss -tln | grep -q 8765 || nohup ...`).

## Manual env (if you want to bypass wrapper)

```bash
export AI_GATEWAY_API_KEY="$OPENCODE_GO_API_KEY"
export FX_MODEL="$OPENCODE_GO_MODEL"
# For loopback http directly (no proxy needed):
export FX_GATEWAY_BASE_URL="http://127.0.0.1:8765"
export FX_GATEWAY_CHAT_URL="http://127.0.0.1:8765/v3/ai/language-model"
fx status
```

## Why not just config?

`fx` only allows loopback http for base URL. External `https` is ignored by design (carries bearer token). Until Vercel adds native `OPENAI_BASE_URL`, proxy is the only bridge.
