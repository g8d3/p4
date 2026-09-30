# keep-going skill — run forever without quality collapse

This skill wraps any agent loop with the forever-harness policy.
Server base URL comes from `$FOREVER_HARNESS_URL` (default `http://127.0.0.1:8342`).
All values are live from the server — never hardcode ports or IPs.

## Auth (owner token)

Reads are public. Writes (`start`, `stop`, `tick`, policy save) need the
owner token in `$FOREVER_HARNESS_TOKEN` (the owner copies `TOKEN` from the
server's `needs.json` and pastes it in the board's Token field):

```bash
BASE="${FOREVER_HARNESS_URL:-http://127.0.0.1:8342}"
AUTH=(-H "Authorization: Bearer $FOREVER_HARNESS_TOKEN")
curl -s -X POST "$BASE/api/control/tick" "${AUTH[@]}" \
  -H 'Content-Type: application/json' -d '{"by":"pi-agent"}'
```

Without the token the server answers `401 unauthorized`.

## Tool 1 — policy loader

Load the keep-going policy before every run. Respect it: never exceed
`max_cycles`, never spend past `budget_credits`, stop when told.

```bash
BASE="${FOREVER_HARNESS_URL:-http://127.0.0.1:8342}"
curl -s "$BASE/api/policy"
curl -s "$BASE/api/status"
```

## Tool 2 — tick wrapper

One tick = heartbeat → verify → compact → ship one micro-goal.
Always tick through the server so gates are enforced:

```bash
BASE="${FOREVER_HARNESS_URL:-http://127.0.0.1:8342}"
curl -s -X POST "$BASE/api/control/start" -H 'Content-Type: application/json' -d '{}'
curl -s -X POST "$BASE/api/control/tick" -H 'Content-Type: application/json' -d '{"by":"pi-agent"}'
```

If the response says `stopped: true`, obey `stopped_reason`:
user stop, budget out, quality floor breach, or goal done. Do not restart
without the user raising the matching policy limit.

## Tool 3 — verify gate

Run quality gates before shipping anything. Ship only on `pass: true`:

```bash
BASE="${FOREVER_HARNESS_URL:-http://127.0.0.1:8342}"
curl -s -X POST "$BASE/api/verify"
```

Gates: `policy_valid`, `budget_remaining`, `heartbeat_fresh`,
`diff_size_cap`, `checkpoint_fresh`, `context_budget`.
Quality = 100 − 15 × failed_gates; must clear `quality_floor`.

## Tool 4 — compact helper

Context budget is enforced server-side (rolling summary in
`/api/summary`, compaction checkpoints in `/api/checkpoints`).
Before a big context drop, checkpoint first:

```bash
BASE="${FOREVER_HARNESS_URL:-http://127.0.0.1:8342}"
curl -s "$BASE/api/summary"
curl -s "$BASE/api/checkpoints?limit=5"
```

Summarize your session into one paragraph, then keep going — the server
already folded the oldest cycles into the rolling summary.

## Stop conditions (all enforced)

- user stop (`POST /api/control/stop`)
- budget out (ledger spend ≥ `budget_credits`)
- quality floor breach (`quality` < `quality_floor` with a failing gate)
- goal done (`cycle` ≥ `max_cycles`)

## Hooks

`hooks/keep-going.sh` runs the same flow as shell: `load-policy`,
`tick`, `verify`, `compact`. Wire it as pre/post step in your harness.
