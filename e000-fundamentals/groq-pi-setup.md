# GROQ provider setup for the pi agent (pi-web)

Last updated: 2026-08-28 (local time; UTC 2026-08-29T02:xx).

Status: **role/config bugs fixed and verified live in pi-web sessions** (including
via the session REST API). Remaining blocker is the GROQ **free-tier TPM limit**
(≈8,000 tokens/min) vs pi's ~18–24k-token requests — needs DEV tier for agent use.

---

## 1. Goal

Use a GROQ model (`qwen/qwen3.6-27b`, …) inside the pi agent (pi-web / session daemon).

## 2. Files changed

| File | Change | Notes |
|------|--------|-------|
| `~/.pi/agent/auth.json` | added `"groq": { "type": "api_key", "key": "<gsk_…>" }` | 0600. Auth source of truth (auth.json > env var) |
| `~/.pi/agent/models.json` | added `providers.groq` with `modelOverrides` (`supportsDeveloperRole:false`) + custom models `qwen/qwen3.8-27b`, `allam-2-7b` | pi reloads models.json on every runtime refresh — no restart needed for content |
| `~/.pi/agent/extensions/sync-opencode-models.ts` | **Bug fix**: rewrote `models.json` with ONLY `opencode-go`, wiping every other provider (groq). Now preserves `existingCfg.providers` minus `opencode-go` | Root cause of "fix disappears" |
| `~/.pi/agent/extensions/zz-groq-restore.ts` | **New guardian extension**: re-ensures the groq provider entry in `models.json` after any wipe (session_start hook + `groq-restore` command) | Needed because the running sessiond caches the OLD compiled sync extension until restart |
| `~/.pi/agent/settings.json` | `enabledModels` — replaced dead groq models with live ones (see §6) | sync extension preserves non-opencode-go entries |
| `~/.bashrc` | moved `source ~/.secrets/.env` to the top (before the non-interactive early-return) so non-interactive shells (pi bash tool) get the keys | `~/.zshrc` already sourced it |

## 3. Root causes found

### 3.1 `400 "Unexpected message role"` (the main bug)

- pi's openai-completions adapter: `useDeveloperRole = model.reasoning && compat.supportsDeveloperRole`.
- Default for a "standard" provider (incl. groq) is `supportsDeveloperRole: true`, so for every **reasoning** groq model pi sent the system prompt with `role: "developer"`.
- GROQ's chat templates (qwen/gpt-oss) only accept `system` / `user` / `assistant` / `tool` → 400.
- Reproduced directly: `curl` with `role:"developer"` fails; `role:"system"` works.
- **Fix**: `compat: { "supportsDeveloperRole": false }` per reasoning model (via `modelOverrides`).

### 3.2 Stale catalog

- `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` no longer exist on GROQ (404 `model_not_found`). Remove from `enabledModels`.
- Live GROQ models (2026-08-28): `allam-2-7b`, `openai/gpt-oss-{20b,120b,safeguard-20b}`, `qwen/qwen3.6-27b`, **`qwen/qwen3.8-27b`** (new, not in pi's built-in catalog → added as custom model), plus whisper/orpheus/compound (voice/agentic).

### 3.3 Extension wipe (why every fix "magically" disappeared)

- `sync-opencode-models.ts` rewrites `~/.pi/agent/models.json` as a **complete** snapshot with only `opencode-go`, destroying any other provider config, on every pi launch **and on every new pi-web session** (the long-lived session daemon runs the version it compiled at its own startup — extension modules are cached per process, so editing the `.ts` does NOT affect the running sessiond until restart).
- Fix: edit the extension to preserve other providers + add `zz-groq-restore.ts` (new file name = new cache key = loaded fresh by the sessiond) which re-ensures groq after wipes.
- After the next `pi-web restart`, the fixed extension loads and zz-groq-restore becomes belt-and-suspenders.

## 4. Verified working models (with a real pi request)

```
pi -p --provider groq --model qwen/qwen3.6-27b --no-session "..."
→ "GROQ OK"        (role bug gone)
pi -p --provider groq --model groq/qwen/qwen3.8-27b ...
→ "GROQ 3.8 OK"    (custom model registered)
openai/gpt-oss-120b → works via curl (reasoning_effort: medium accepted), TPM-limited in pi
```

## 5. Remaining blocker: GROQ free-tier TPM

- GROQ free (`on_demand`): **8,000 tokens/minute**.
- pi's request floor: ~18,000 tokens **even with** `--no-tools` + a 5-word `--system-prompt`; ~21–24k with the normal coding-agent prompt (tool schemas). One pi request > TPM budget → `413 Request too large` (the error reports `Requested <N>` vs `Limit 8000`).
- A plain curl with a small payload (~57 tokens) works fine — so the key/model/params are all correct.
- **Path forward**: upgrade to GROQ DEV tier (no config changes needed) or keep GROQ for light/scripted requests.

## 6. Does the model picker show GROQ?

`enabledModels` (global scope) currently includes (after wiping the dead llamas):

```
groq/allam-2-7b
groq/openai/gpt-oss-120b
groq/openai/gpt-oss-20b
groq/openai/gpt-oss-safeguard-20b
groq/qwen/qwen3.6-27b
groq/qwen/qwen3.8-27b
```

Note: the running sessiond caches the enabled-models scope at startup; a UI toggle or a pi-web restart refreshes it.

## 7. Trick: sending messages to another pi-web session (REST)

pi-web sessions are REST resources on the session daemon; the web server (port 8504) proxies them under `/api/machines/local/*`. **No auth on localhost.**

```bash
BASE=http://localhost:8504/api/machines/local/sessions/<sessionId>

# inject a user message
curl -X POST "$BASE/prompt" -H "Content-Type: application/json" \
  -d '{"cwd":"/home/vuos/code/p4","text":"hi from session <other>"}'
# → {"accepted":true}

# re-select the model (re-resolves against the fresh catalog — applies config fixes)
curl -X POST "$BASE/model" -H "Content-Type: application/json" \
  -d '{"cwd":"/home/vuos/code/p4","provider":"groq","modelId":"qwen/qwen3.6-27b"}'

# list / refresh the model catalog
curl "$BASE/models/catalog?cwd=/home/vuos/code/p4"
```

Results are read from the session transcript:
`~/.pi/agent/sessions/--home-vuos-code-p4--/<sessionId>.jsonl` (append-only JSONL; printed tool output also lands there).

### Security note

- `pi-web` config (`~/.config/pi-web/config.json`) currently binds **`0.0.0.0:8504`** with **no authentication** — reachable from the LAN/tailnet (observed requests from a tailscale IP). Anyone with port access can message/inspect sessions.
- Suggested hardening: `"host": "127.0.0.1"` (or configure `allowedHosts`), then `pi-web restart`.

## 8. Secrets hygiene policy (learned the hard way 2026-08-28)

- Incident: during the setup, full contents of `~/.secrets/.env` and `auth.json` were echoed into a session transcript (0644) — all API keys, wallet keys, tokens exposed in that file.
- Remediation: scrubbed all known secret values from **every** session transcript under `~/.pi/agent/sessions/` and the `/tmp/pi-bash-*.log` leftovers (values → `[REDACTED]`, JSONL kept valid), verified by masked re-scan.
- Policy going forward:
  - **Never** `cat`/`read`/echo `~/.secrets/.env` or `auth.json` contents into a session.
  - Scripts read secret files without printing values; verification is masked only (`key=sk-h0T…0wFi (len 67)`).
  - Users rotating keys should edit `~/.secrets/.env` themselves (not paste into chat), then a masked sync updates `auth.json`.
  - Audit reminder: the `opencode-go` key had previously been exposed in old p3 session files (May 2026) — scrubbed; consider rotating.

## 9. TODO / follow-ups

- [ ] `pi-web restart` (loads the fixed sync extension + zz-groq-restore; refreshes scope) — ideally right before the user wants groq usable per-session.
- [ ] GROQ DEV tier if pi should really run on groq models.
- [ ] Harden pi-web bind (127.0.0.1 or allowedHosts).
- [ ] Optionally rotate the exposed `opencode-go` key.