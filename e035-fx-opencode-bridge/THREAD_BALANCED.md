# X thread — balanced for AI tool users (each <140 chars)

1/10 I use fx by Vercel (12MiB Zig, native, fast) and opencode-go ($10/mo, DeepSeek/Muse/GLM via opencode.ai).

2/10 fx is great — tiny and fast — but locked to Vercel's gateway. I wanted it to burn my $10 opencode credit.

3/10 Tried `FX_GATEWAY_BASE_URL=https://opencode.ai/zen/go/v1/` — ignored. `fx status` still `zai/glm-5.2`. No error.

4/10 Found in Zig source: only `http://127.0.0.1:port` allowed. External https is silently dropped.

5/10 Fix: tiny translator on `127.0.0.1:8765`. fx thinks it's Vercel, translator talks OpenAI to opencode.

6/10 First try: `403 code 1010`. curl worked. Cloudflare blocked `Python-urllib`. Fix: `User-Agent: fx/0.0.4`.

7/10 Next: `StreamInterrupted x10`. Vercel SSE (`text-delta`/`finish`) != OpenAI SSE. Built a translator.

8/10 Then `400` loop: empty `tool_call_id` + nested `tool-result`. OpenAI rejected. Fix: parse inner or → `user`.

9/10 Result: `fx status` → `muse-spark-1.2-contributor`, `fx ask --yolo "list files"` works. Any tmux window: `fx`.

10/10 If your AI tool ignores `BASE_URL`: check localhost-only, `User-Agent` blocks, SSE dialect. Wrapper at `~/.local/bin/fx`.

11/11 Code + 2-command install: github.com/g8d3/p4/tree/master/e035-fx-opencode-bridge — patch fx to use opencode-go.
