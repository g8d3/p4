# One-liner patch — use opencode models with fx

> Until `fx` adds native `opencode-go` support, this bridge lets you burn your $10 credit via `fx`.

## Patch / unpatch in one command

```bash
# patch using your current OPENCODE_* env (from ~/.hermes/.env)
bash e035-fx-opencode-bridge/bin/install.sh

# patch with literal values (no env needed)
OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1/ OPENCODE_GO_API_KEY=sk-... OPENCODE_GO_MODEL=muse-spark-1.2-contributor bash e035-fx-opencode-bridge/bin/install.sh
# or: bash bin/install.sh patch https://opencode.ai/zen/go/v1/ sk-... muse-spark-1.2-contributor

# unpatch (restore Vercel)
bash e035-fx-opencode-bridge/bin/install.sh unpatch

# via curl (no clone) — short URL:
curl -fsSL https://tinyurl.com/283mqya5 | bash
curl -fsSL https://tinyurl.com/283mqya5 | bash -s unpatch
# long URL also works:
# curl -fsSL https://raw.githubusercontent.com/g8d3/p4/master/e035-fx-opencode-bridge/bin/install.sh | bash
```

The patch is a `PATH` shadow (`~/.local/bin/fx` → `fx.real` + proxy at `127.0.0.1:8765`), not a recompile. To update `fx` later: `fx upgrade` (wrapper survives), or `bash install.sh unpatch` before.

## What it does

- `OPENCODE_GO_API_KEY` → `AI_GATEWAY_API_KEY`
- `OPENCODE_GO_MODEL` → `FX_MODEL`
- `OPENCODE_GO_BASE_URL` (https) → `FX_GATEWAY_BASE_URL=http://127.0.0.1:8765` via `fx-opencode-proxy.py`

`fx` only trusts `http://127.0.0.1`, so external `https` is ignored without the proxy. Proxy translates Vercel SSE ↔ OpenAI.

## Use after patch

```bash
fx status # → model=muse-spark-1.2-contributor
fx ask --yolo "list files" --no-save
# new tmux window:
tmux new-window -n fx2 -d; tmux send-keys -t fx2 "fx" Enter
```

Note: bridge until `fx` supports `opencode-go` natively. Long-term fix is `isLoopbackHttpUrl` → allow `https://opencode.ai`.
