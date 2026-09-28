# e081 — OpenCode Go usage (one-command quota check)

One command that prints your OpenCode Go rolling / weekly / monthly
usage percentages. Built because looking these up by hand took a full
research session; next time any agent just runs the script.

## Product

| Surface | User action |
|---|---|
| `bin/usage.sh` | Run it, read `rolling X% / weekly Y% / monthly Z%` with reset times. No login, no thinking. `--json` for raw API output. |

Rule: stdlib only, no deps. All machine values come from env/settings
documented in `needs.json` — never buried in code.

## Architecture

```
needs.json     ALL config: base URL env, key envs, endpoint path, defaults
bin/usage.py   stdlib python3: GET {base}/usage, Bearer key, prints 3 lines
bin/usage.sh   thin wrapper so agents call one stable path
test/check.sh  runs script, asserts rolling/weekly/monthly present + --json valid
```

## Run

```bash
bin/usage.sh          # human: 3 lines with reset times
bin/usage.sh --json   # raw API JSON
test/check.sh         # smoke test (needs a valid key in env)
```

## DONE ladder

1. WORKING — `test/check.sh` PASS with live key.
2. DEPLOYED — n/a (CLI only, no server).
3. TESTED — output contains all 3 windows; `--json` parses.
4. ANNOUNCED — owner runs `bin/usage.sh` once.
5. MONETIZED — n/a.
