# e035 — fx + opencode bridge

Make `fx` (Vercel's tiny native agent, `0.0.4`, 12MiB Zig) respect p4's `OPENCODE_*` env vars. The user pays $10/mo for `opencode-go` (subscription at opencode.ai) and wants fx to burn *that* credit, not Vercel's.

## The lie

You'd think `fx` would just read `OPENCODE_GO_BASE_URL` like `opencode` does. It doesn't. fx is hard-wired to `https://ai-gateway.vercel.sh`.

- `FX_MODEL` → works (overrides `~/.fx/settings.json`).
- `AI_GATEWAY_API_KEY` → works (alternative to `fx login`).
- `FX_GATEWAY_BASE_URL` / `FX_GATEWAY_CHAT_URL` → **only `http://127.0.0.1|localhost|[::1]:port`**. Anything else is silently ignored.

Check the source:

```zig
// src/gateway/client.zig:591
if (!isLoopbackHttpUrl(override)) {
  debug_trace.logf("stream", "ignoring FX_GATEWAY_BASE_URL: not loopback http", .{});
  return default_gateway_base_url; // https://ai-gateway.vercel.sh
}
```

```zig
// src/builtins/gateway.zig:752
if (!gateway_client.isLoopbackHttpUrl(candidate)) return fallback;
```

So `export FX_GATEWAY_BASE_URL=https://opencode.ai/zen/go/v1/` does absolutely nothing. No error, just ignored. That's pain point #1.

## Pain points (the real 2.5h)

**Hour 0 - The invisible wall.** `fx status` kept showing `zai/glm-5.2` even after `export FX_GATEWAY_BASE_URL=...`. Spent 40min grepping `strings fx | grep -i gateway`, curling `fx.sh/docs`, cloning `vercel-labs/fx` source via `raw.githubusercontent.com` until we found the loopback check. The `FX_TRACE_LOG` trick finally showed `ignoring FX_GATEWAY_BASE_URL: not loopback http`.

**Hour 1 - Cloudflare hates Python.** Built a loopback proxy at `127.0.0.1:8765` to forward `POST /v3/ai/language-model` → `POST https://opencode.ai/zen/go/v1/chat/completions`. First version got `403 error code: 1010` on every `GET /models` and `POST`. Direct `curl` worked fine. Turns out Cloudflare blocks `Python-urllib/3.12`. Fix: `User-Agent: fx/0.0.4`.

**Hour 1.5 - SSE hell.** fx expects Vercel gateway SSE: `data: {"type":"text-delta","delta":"hi"}` → `data: {"type":"finish","finishReason":{"unified":"stop"}}` → `data: [DONE]`. We were forwarding OpenAI SSE verbatim. fx saw `StreamInterrupted` and retried 10 times (5× `63030` byte payloads in `~/.cache/fx-proxy.log`). Fix: translate `delta.content` → `text-delta`, accumulate `tool_calls` → `tool-input-start/delta/end` + `tool-call`, and *always* emit a synthetic `finish` when upstream omits `finish_reason` (opencode often returns `choices:[]` with no reason).

**Hour 2 - Ghost tools.** `fx ask --yolo "list files"` succeeded in `ls -la` but then looped with `400` and empty `{"role":"assistant"}`. The gateway's second-turn history has a `tool` message with `content: [{type:"tool-result", toolCallId, output:{value}}]` and empty `tool_call_id` at top level. OpenAI rejected it as `tool message without preceding tool_calls`. Fix: parse the inner `tool-result` array, extract `toolCallId` and `output.value`, and if no preceding `assistant.tool_calls`, convert the orphan to a `user` message: `[Tool list_files result]\n...`. Also filter the `<network_recovery>` system message fx injects on retry.

**Hour 2.3 - tmux confusion.** User said “start it on tmux window 1” — we put the *proxy* there, user meant *fx*. Classic. Killed `33171`, restarted proxy via `nohup` (`33716`), and launched `fx` in `main:1` (`tmux send-keys -t main:1 "fx" Enter`). Now `main:1` shows `auto · muse-spark-1.2-contributor` (not `zai/glm-5.2`).

## What we built

```
~/.local/bin/fx              # 3418B wrapper (was 12M binary, now at fx.real)
~/.local/bin/fx.real         # original binary
~/.local/bin/fx-opencode-proxy.py  # 470 lines, ThreadedTCPServer on 127.0.0.1:8765
~/.local/bin/fx-wrapper.sh   # same as wrapper, for reference
~/.cache/fx-proxy.log        # proxy log
~/.config/systemd/user/fx-opencode-proxy.service # optional persistent
~/.zshrc:330                 # now just a comment, wrapper in PATH handles everything (including `timeout fx`)
```

Wrapper logic:

```bash
if [[ -n "$OPENCODE_GO_API_KEY" ]]; then export AI_GATEWAY_API_KEY="$OPENCODE_GO_API_KEY"; fi
if [[ -n "$OPENCODE_GO_MODEL" ]]; then export FX_MODEL="$OPENCODE_GO_MODEL"; fi
if [[ "$OPENCODE_GO_BASE_URL" == http://127.0.0.1* ]]; then
  export FX_GATEWAY_BASE_URL="$base" # direct
else
  # external https → loopback proxy
  ss -tln | grep -q 8765 || nohup python3 ~/.local/bin/fx-opencode-proxy.py > ~/.cache/fx-proxy.log 2>&1 &
  export FX_GATEWAY_BASE_URL="http://127.0.0.1:8765"
  export FX_GATEWAY_CHAT_URL="http://127.0.0.1:8765/v3/ai/language-model"
fi
exec ~/.local/bin/fx.real "$@"
```

## How to use (new tmux window)

The wrapper is in `PATH`, so any `fx` invocation works. No manual env.

```bash
# In any shell (existing env already has OPENCODE_GO_* from .hermes/.env)
fx status --json # → {"model":"muse-spark-1.2-contributor", ...}
fx ask "explain src/" --no-save
fx ask --yolo "list files" --no-save

# New tmux window (the way you asked):
tmux new-window -n fx2 -d
tmux send-keys -t fx2 "fx" Enter
# or one-off:
tmux new-window -n tmp -d
tmux send-keys -t tmp "fx ask --yolo 'hi' --no-save" Enter

# If proxy dies (after reboot):
cat ~/.cache/fx-proxy.log
# wrapper auto-restarts it on next fx call, or:
nohup python3 ~/.local/bin/fx-opencode-proxy.py > ~/.cache/fx-proxy.log 2>&1 &
# or systemd:
systemctl --user enable --now fx-opencode-proxy
```

Port is `FX_PROXY_PORT=8765` (override via env). To disable tools forwarding (if 403 returns): `FX_PROXY_DISABLE_TOOLS=1`.

## Verification

```
$ fx status
[status] model=muse-spark-1.2-contributor  # ← from OPENCODE_GO_MODEL
$ curl -s http://127.0.0.1:8765/coding-agent/v1/models | jq '.models[0].id'
"muse-spark-1.2-contributor"
$ timeout 30 fx ask --yolo "say hello in one word" --no-save
hello
```

## Time

~2.5h wall time (20 Aug 2026 16:45–19:10). 80% was reading Zig source and debugging invisible failures. The actual code is 3 files, 500 lines.

## Future

If `fx` ever adds `OPENCODE_GO_BASE_URL` or `OPENAI_BASE_URL` natively, delete the proxy. Until then, this bridge burns opencode credit via fx.

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, quiet mode, AgentFS
