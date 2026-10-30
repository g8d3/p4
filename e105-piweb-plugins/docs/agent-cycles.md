# Agent cycles — design notes

The problem, in the words it was reported: restarting PI WEB drops every working
agent. They do not come back on their own; today an external script notices the
restart and writes to the agents that were working so they resume. That external
script is doing two different jobs, and they belong in two different places.

## The two jobs

1. **Noticing and remembering** — who was working, on what, when the daemon went
   down, and which of them came back. This is observation: session metadata,
   start/stop times, last activity. A PI WEB plugin can do it (server entry reads
   sessions, browser entry shows the cycle).
2. **Writing to them** — resuming a conversation means dispatching a prompt into a
   session. That is agent-side behavior, and the documented path for it is a **Pi
   extension** (`spawn_session` / dispatch with a prompt), not a PI WEB plugin.
   A plugin cannot resurrect an agent by itself.

So the honest split is: **plugin = eyes, extension = hands.** Building only the
plugin would produce a panel that tells you agents are down and cannot do anything
about it. Building only the extension would act invisibly. Both, and the cycle is
complete.

## What the cycle needs to know

Per agent session, the plugin keeps a small, append-only ledger:

```json
{"session": "01a188...", "cwd": "/home/vuos/code/p4", "title": "likes_web",
 "state": "working", "since": "2026-10-30T01:12:00Z", "last_output": "…",
 "daemon_boot": "boot-2026-10-30T01:12:04Z", "resumed_by": null}
```

* `state` is derived, never typed: working while the session is streaming, idle
  when it answered, orphaned when the daemon boot id changed and the session did
  not come back within a grace window.
* `daemon_boot` is what makes "the restart orphaned it" a fact instead of a guess.
* A cycle is the set of sessions that were working at a given boot.

## The grace window

Resuming too early fights the daemon (the session may still be recovering);
waiting forever loses work. The design uses one grace window per boot
(default 90 s), then acts once per session, and records that it acted. Nothing
resumes twice: `resumed_by` is written before the prompt is dispatched.

## What the user sees

An application tab **Cycles** with one row per cycle:

| Cycle | Down at | Agents working | Resumed | Not resumed (why) |
|---|---|---|---|---|
| boot-2026-10-30T01:12 | 01:12 | 3 | 2 | 1 (workspace deleted) |

Each row can open the session. A button "resume the ones that did not" exists so
the action is never only automatic. The panel says plainly which agents it could
not restore, because a silent failure here looks exactly like an agent that chose
to stop.

## What it must not do

* **No secret reading, no model calls, no spending.** Resuming is a prompt, not a
  new task.
* **No retry storms:** one attempt per session per boot, with the attempt written
  down before it happens.
* **No guessing:** an agent whose state cannot be read is shown as unknown, not as
  orphaned. A wrong "resumed" is worse than an honest blank.

## Build order

1. **Ledger** (server entry): read sessions, write the boot id, keep the append-only
   file in the plugin's own data directory. No UI yet. This alone answers "what
   did the last restart orphan?".
2. **Panel** (browser entry): the Cycles table above, read-only.
3. **Dispatch** (Pi extension): the piece that actually re-prompts, using the
   documented hosted-extension dispatch, gated by the ledger so it runs once.
4. **Integration with TPS**: show, per cycle, what those agents had cost and how
   much of the work was lost — that is the number that decides whether resuming is
   worth it.

Steps 1-2 are a PI WEB plugin and need a session-daemon restart to load a server
entry. Step 3 is a separate package and needs `/reload`. The catalog panel
(`p4.catalog`) already lists this as *designed, not built* so nobody assumes it
exists.

## Restart orchestration (what was discussed on 2026-10-30)

The operator's instinct was: the restart should be part of this work, from an external process, and
the agents that were working must be told to continue afterwards. That is right, with one correction:
the *plugin* cannot own the restart, because a plugin with a server entry only loads after a daemon
restart (chicken and egg), and the browser cannot kill the process hosting it. The owner is an
**external orchestrator**, and the panel is where you see the result.

`scripts/restart-orchestrator.py` implements the five steps:

1. **detect** — sessions that wrote in the last `--active-window` seconds are the ones a restart would
   hurt. Nothing else is protected, so nothing else is touched.
2. **quiesce** — wait until *nothing* writes for `--quiesce-seconds`; `--max-wait` then aborts with
   nothing killed. Killing an agent mid-tool-call is how work is lost and locks are left behind, so
   the orchestrator would rather do nothing than restart in the middle of a turn.
3. **restart** — `systemd-run --user --collect --on-active=2 systemctl --user restart
   pi-web-sessiond`: a transient unit, so the restart is not a child of the daemon it kills.
4. **resume** — `POST /api/machines/local/sessions/<id>/prompt` with `{cwd, text}` (the same endpoint
   the web client uses; verified: a bad id answers `404 {"error":"Session not found"}`, so the payload
   is right). Attempts are appended to `.pi-web/agent_resumes.jsonl` **before** dispatching, so a
   crash cannot resume the same session twice.
5. **report** — `.pi-web/restart_state.json` plus the ledger the Cycles panel reads.

Default is `--plan`; `--execute` is required to change anything.

### Decoupling the web from the agents (the better answer)

The operator asked whether decoupling is better. It is, and half of it is already true: PI WEB runs
two processes — `pi-web` (web/API, port 8504) and `pi-web-sessiond` (which hosts the agents). So:

* restarting the **web** kills no agent, ever;
* restarting the **session daemon** kills all of them — it is the only process a normal update forces
  us to restart, because server plugins load there.

The rest of the decoupling (an agent runtime that outlives a daemon restart) is upstream work; until
then the orchestrator is the honest way to restart without losing the work in flight.
