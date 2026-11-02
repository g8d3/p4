# e107 play notes — dsh-superagent prototype

## Why it matters (money link)

The bottleneck for an agent network that earns is **attention cost**: every message,
PR, ping costs a human's time. This prototype is the only public DeepSeek code that
treats attention as the budget and builds the whole system (Policy → Eval → Ticket →
Executor → panel) around spending as little of it as possible. If our agents are going
to serve paying users through a browser extension, the Policy/admission-table and
"quiet by default" panel rules here are directly reusable — they decide what the agent
is *allowed* to do and what it *bothers a person* about. That is the difference between
a sellable service and a noisy toy.

## What I ran

| Step | Result |
|---|---|
| `pnpm install` | OK, 13.4 s |
| `pnpm typecheck` (`tsc --noEmit`) | OK |
| `pnpm build` (tsdown) | OK, 6.3 s, `lib/` 11 files 693 KB |
| `pnpm test` (vitest, 59 files) | 1196 passed, **1 failed** |

## The one failure

Test: `tests/sources.spec.ts` → "takes in the event lines it reads, records each
chat as direct or not, and reports a malformed line without stopping".

Setup: fake `lark-cli` prints `[event] ready` on stderr, then cats an events file
with 4 stdout lines: `om_1` (group), `om_2` (p2p), literal `not json`, `om_3` (group).

Expectations that pass: triggers stored, `direct` flags `[false, true]`, chats map
`{oc_group: false, oc_dm: true}`, `om_3` present.

Failing assertion (line 1097):

```ts
expect(health.feishu).toMatchObject({ state: 'error', detail: expect.stringContaining('JSON') })
```

Actual: `{ state: 'ready', detail: 'Listening for bot events' }`.

Reading `src/sources/feishu-loops.ts` `consume()`: stdout lines are chained through
`chain.then(JSON.parse …).catch(report error)`, stderr `[event] ready` reports ready.
`JSON.parse('not json')` does throw (`Unexpected token 'o', "not json" is not valid
JSON`, verified on node 24), so the `.catch` should overwrite health with `error`.
It doesn't — the error report never lands. Repro is deterministic (full suite +
`-t "malformed line"` isolated). Single-commit repo, so this ships upstream.

Possible causes (not yet bisected): report filtering through `sourceContextOf` /
`HealthBoard.claim`, or the `chain` catch writing to a stale entry. Good first bug
for whoever does the live spike — the consumer silently swallows malformed events
while looking healthy, which is exactly the class of quiet-data-loss the philosophy
doc says must be loud.

## Architecture in 60 seconds

- **Domain** (`src/core/`): Source → Trigger → Thread → Eval (gate + assessment) →
  Decision (accept/stop/ignore/unavailable) → Ticket + Mandate → Assignment → Executor.
  Subscriptions fan out later messages to live Tickets without new Eval; handbacks
  return out-of-scope work to Eval. Engine is sync + transactional; ports enqueue
  side effects performed after commit.
- **Sources** (`src/sources/`): GitHub (notifications, issues/PRs, CI, merge/close) and
  Feishu (live events, history backfill, topic polling). Adding a Source = map events to
  Trigger/Thread/Channel + config schema + health + polling loop (008-cookbook has a
  full `webhook` recipe).
- **Executor**: one DSH Session (`worker-<ticket>`) + one directory per Ticket, 5 s
  shell→background rule so long commands never block incoming messages, worker slots
  with one extra slot reserved for human wake-ups, 30 min background cap, prepare
  command (typically `git worktree`) with 10 min timeout.
- **Prompts** (`prompts/`): orchestrator/router + worker split, team-overridable sections,
  admission/assessment/delivery rules as text, not settings.
- **Panel** (`src/app/views/` + `src/client/`): Overview → Source → Trigger → Eval →
  Execution → Settings, "does anything need me / is it healthy / what is the history".
- **Settings**: versioned Policy (rules + accept mode `observe|auto|off` + per-Source
  allowed lists, admission table, bot list). Saves go through the Management API;
  bad saves name the setup problem (account/CLIs/stateDir).

## What I did NOT do

No live run: needs `dsh@0.2.1-rc.3` binary + a dedicated agent GitHub account with
repo write access + `superagent` profile. Deliberately stopped before creating accounts —
that is an operator step per upstream SETUP.md. The toolchain here has node 24, pnpm
11.7.0, gh 2.45.0, tmux; `dsh` is not installed.

## Next concrete step

```sh
npm install -g @deepseek-ai/dsh@0.2.1-rc.3
git clone https://github.com/deepseek-ai/dsh-superagent-prototype dsh-superagent
cd dsh-superagent && pnpm install && pnpm build
dsh superagent --from-default-profile web --dump-config > /dev/null
dsh plugin --profile superagent add "link:$PWD"
# then SETUP.md with a scratch repo + dedicated agent account
```

Suggested first live test: scratch repo, allowed list = owner only, accept mode
`observe`, comment `@agent <request>` on an issue, watch Ticket appear in
Overview within ~1 min, then flip to auto for one small fix PR.
