# How to patch `fx` to use `opencode-go`

> `fx` is hardcoded to Vercel. This patch makes it use your $10 `opencode-go` subscription.

## What "patch" means here

We don't recompile Zig. We **wrap** the binary:

- `~/.local/bin/fx` (12M ELF) → `~/.local/bin/fx.real` (backup)
- `~/.local/bin/fx` (new, 3418B shell) → sets `FX_*`/`AI_GATEWAY_*` from `OPENCODE_*`, starts proxy if needed, then `exec fx.real`

It's a `PATH` shadow, so `fx`, `timeout fx`, `tmux send-keys "fx"` all go through it.

## Why a proxy?

`fx`'s `isLoopbackHttpUrl` check:

```zig
// src/gateway/client.zig:591, src/builtins/gateway.zig:752
if (!isLoopbackHttpUrl(override)) {
  log("ignoring FX_GATEWAY_BASE_URL: not loopback http");
  return default; // https://ai-gateway.vercel.sh
}
```

```bash
export FX_GATEWAY_BASE_URL=https://opencode.ai/zen/go/v1/ # ignored, no error
```

Only `http://127.0.0.1:port` is accepted. Your opencode URL is `https://...`, so we expose it via `http://127.0.0.1:8765` that translates:

```
fx --(Vercel SSE)--> 127.0.0.1:8765 --(OpenAI JSON)--> https://opencode.ai/zen/go/v1/chat/completions
       text-delta / tool-call / finish  <-  delta.content / tool_calls  <- 
```

Without the proxy, `AI_GATEWAY_API_KEY=$OPENCODE_GO_API_KEY` would still hit Vercel and get `401`.

## Replicate (2 commands)

```bash
# 1. Copy this experiment's bin/ and run installer
cp -r e035-fx-opencode-bridge/bin/* ~/.local/bin/ # or
bash e035-fx-opencode-bridge/bin/install.sh

# 2. Use it (env already has OPENCODE_GO_* from ~/.hermes/.env)
fx status --json # should show "model":"muse-spark-1.2-contributor" not "zai/glm-5.2"
fx ask --yolo "list files" --no-save
```

## Manual patch (what install.sh does)

```bash
# backup
cp ~/.local/bin/fx ~/.local/bin/fx.real

# wrapper (sets env, starts proxy if https)
cp e035-fx-opencode-bridge/bin/fx ~/.local/bin/fx
chmod +x ~/.local/bin/fx
# ensure it points to fx.real
sed -i 's|REAL_FX="$HOME/.local/bin/fx"|REAL_FX="$HOME/.local/bin/fx.real"|' ~/.local/bin/fx

# proxy
cp e035-fx-opencode-bridge/bin/fx-opencode-proxy.py ~/.local/bin/
chmod +x ~/.local/bin/fx-opencode-proxy.py

# optional daemon
cp e035-fx-opencode-bridge/bin/fx-opencode-proxy.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now fx-opencode-proxy
```

Wrapper snippet (`~/.local/bin/fx`):

```bash
if [[ -n "$OPENCODE_GO_API_KEY" ]]; then export AI_GATEWAY_API_KEY="$OPENCODE_GO_API_KEY"; fi
if [[ -n "$OPENCODE_GO_MODEL" ]]; then export FX_MODEL="$OPENCODE_GO_MODEL"; fi
if [[ "$OPENCODE_GO_BASE_URL" == http://127.0.0.1* ]]; then
  export FX_GATEWAY_BASE_URL="$base"
else
  ss -tln | grep -q 8765 || nohup python3 ~/.local/bin/fx-opencode-proxy.py > ~/.cache/fx-proxy.log 2>&1 &
  export FX_GATEWAY_BASE_URL="http://127.0.0.1:8765"
  export FX_GATEWAY_CHAT_URL="http://127.0.0.1:8765/v3/ai/language-model"
fi
exec ~/.local/bin/fx.real "$@"
```

Proxy (`fx-opencode-proxy.py`, 470 lines):

- `GET /coding-agent/v1/models` → `GET $OPENCODE_GO_BASE_URL/models` with `User-Agent: fx/0.0.4` (Cloudflare blocks `Python-urllib`)
- `POST /v3/ai/language-model` → `POST $OPENCODE_GO_BASE_URL/chat/completions` with `model` stripped of `meta/` prefix, `prompt` → `messages`, `tools` → OpenAI functions, `tool` results with `toolCallId` extraction, `<network_recovery>` filter, SSE `text-delta`/`tool-input-*`/`tool-call`/`finish` translation + synthetic `finish` if upstream omits it.

## How to use after patch

```bash
# any shell, any tmux window — wrapper auto-sets env + auto-starts proxy
fx                          # interactive, in tmux: tmux new-window -n fx2 -d; tmux send-keys -t fx2 "fx" Enter
fx ask "explain src/" --no-save
fx ask --yolo "write a test and run it" --no-save

# check:
fx status # model=muse-spark-1.2-contributor
curl -s http://127.0.0.1:8765/coding-agent/v1/models | jq .models[0].id
cat ~/.cache/fx-proxy.log | tail

# change model:
OPENCODE_GO_MODEL=deepseek-v4-flash fx ask "hi" --no-save

# disable tools forwarding if 403 returns:
FX_PROXY_DISABLE_TOOLS=1 fx ask ...

# stop proxy (don't use pkill, it hangs):
ps -o pid,args | grep fx-opencode
kill <PID>
```

## Unpatch

```bash
mv ~/.local/bin/fx.real ~/.local/bin/fx
rm ~/.local/bin/fx-opencode-proxy.py
systemctl --user disable --now fx-opencode-proxy 2>/dev/null; kill $(cat ~/.cache/fx-proxy.pid 2>/dev/null) 2>/dev/null
```

## Files in this experiment

- `bin/fx` — wrapper
- `bin/fx-opencode-proxy.py` — proxy
- `bin/fx-opencode-proxy.service` — systemd
- `bin/install.sh` — installer
- `TIMELINE.md` — measured times (2:21 wall)
- `THREAD*.md` — X threads (<140c)
- `AGENTS.md` / `README.md`
