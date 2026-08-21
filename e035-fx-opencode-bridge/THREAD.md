# X thread — fx + $10 opencode (each <140 chars)

1/10 I pay $10/mo for opencode-go. Love Vercel's fx (12MiB Zig). Want fx to use my opencode credit, not Vercel's.

2/10 `export FX_GATEWAY_BASE_URL=https://opencode.ai/zen/go/v1/` — should work? Nope. Silently ignored.

3/10 `fx status` stays `zai/glm-5.2`. No error. Found in Zig: `if (!isLoopbackHttpUrl) return default;`

4/10 fx only allows `http://127.0.0.1:port`. External https is dropped. Invisible wall.

5/10 Fix: loopback proxy `127.0.0.1:8765 → opencode.ai`. Built in Python. Got `403 code 1010`.

6/10 Direct curl works. Proxy blocked. Cloudflare hates `Python-urllib/3.12`. Fix: `User-Agent: fx/0.0.4`.

7/10 Next: `hello` then `StreamInterrupted x10`. fx expects Vercel SSE, we sent OpenAI SSE.

8/10 Built translator: `delta.content→text-delta`, `tool_calls→tool-input-*` + `tool-call`, always emit `finish`.

9/10 `list files` → `ls -la` works, then `400` loop. Ghost tool: empty `tool_call_id` + `tool-result` array.

10/10 Fix: parse `tool-result`, orphan→`user`, filter `<network_recovery>`. Wrapper `~/.local/bin/fx` maps `OPENCODE_*→FX_*`.

Bonus: `main:1` → `fx` (`tmux send-keys -t main:1 "fx" Enter`), proxy bg `33716`. `fx status` → `muse-spark-1.2-contributor`
