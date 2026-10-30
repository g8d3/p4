# Improvements requested by Nova (in his words, then what it means)

Numbered as received. Nothing here is "done" until it is verified; the state column says which.

## 1. Stop smartly, never on a timer
> "You don't need to wait an arbitrary number of seconds, you need to stop everyone smartly
> (this is hard because we haven't thought what smart is in this case), then you stop it,
> then I reload browser... then you send a message to paused sessions to continue what they
> were doing. But if you already decoupled pi web from agents then you simplify a lot of this.
> No long waits, and no dumb waits: a dumb wait is one that doesn't know what the hell is
> happening (arbitrary number)."

**What it means.** Today the orchestrator waits for "6 seconds with no transcript writes". That is
exactly the dumb wait he is describing: it infers state from file mtimes instead of knowing it.

**What "smart" has to be built on.** A condition someone reports, not a duration:
* a session is **mid-turn** when its event stream shows a turn start without the matching end
  (the TPS companion already consumes `message_start` / `message_update` / `message_end`);
* a session is **idle** when the last observed event closed its turn and nothing is queued
  (the daemon exposes a per-session queue);
* a session we cannot observe is **unknown**, and unknown is never treated as idle.

**The rule that separates a bounded wait from a dumb one:** a timeout may only *cancel* — it can
never grant permission to proceed. "I could not confirm idle within N" aborts the restart; it never
turns into "probably fine, go ahead".

**Browser.** `EventSource` reconnects by itself (that is its default behaviour), so reconnection is
free; a full reload should only be needed if a plugin UI changed, not to recover from a restart.
Verify once, then stop mentioning it.

**The real fix, and his own conclusion.** All of this exists because the agent runtime lives inside
the process we must restart. Decouple the runtime from the web/API layer and the problem disappears
instead of being managed: a web restart interrupts nothing, nothing needs quiescing, nothing needs
resuming, no wait exists at all. Until that upstream split exists, the orchestrator should be
condition-based, and honest about the case where it cannot see.

State: **designed, not built.**

## 2. Short command, fast command
> "All of this process should be as optimized as possible: a short command, and a fast command."

**Short.** What I ran today was this, and it is not acceptable as a daily command:

```
systemd-run --user --collect --unit=p4-restart-resume-2 --on-active=70 \
  --property=WorkingDirectory=/home/vuos/code/p4 --setenv=P4_WORKSPACE=/home/vuos/code/p4 \
  /usr/bin/python3 /home/vuos/code/p4/e105-piweb-plugins/scripts/restart-orchestrator.py \
  --execute --cwd /home/vuos/code/p4 --quiesce-seconds 6 --max-wait 180 --resume-wait 40
```

Target: **one word on PATH.** `piweb-restart` does the whole thing with no flags; `piweb-restart --dry`
shows the plan. Everything that is currently a flag is a default that should be derived, not typed.

**Fast.** Speed must come from knowing, not from sleeping (item 1). The floor is set by the things
that genuinely cost time: the daemon restart itself and the readiness of its socket. So the target is
the honest minimum — measure `command -> last session resumed` and report p50/p95 every run, so a
regression becomes a number instead of a feeling. If a run needs to sleep, the log must say which
condition it was waiting on and how long that condition took, never "waited 6 s".

State: **planned.**

## 3. It should be audited
> "It should be audited too."

**What an audit has to be here.** Not a printout that the command ran. An append-only record per run
that answers, after the fact and without me: who or what asked for the restart, what state each
session was in when it was decided (and on what evidence), what was stopped and how, what was
resumed, and — the part that is easy to skip — **whether the resume actually worked**.

**Attempt is not outcome.** Today a resumed session shows `200` from the prompt endpoint and nobody
knows if the agent continued. The audit must compare intent to reality: the sessions active before
the restart against the sessions that wrote afterwards. A session that was "resumed" with HTTP 200
and never wrote again is a **failed** resume, and the audit says so.

**Rules it follows (same as the rest of this project):**
* append-only, one JSON line per event, never rewritten (`estado/` or `.pi-web/`, gitignored);
* a run that cannot verify its own outcome is recorded as `unverified`, never as success;
* failures are loud: a report line, and the Cycles panel shows the restart as "resumed N, lost M";
* the same minutes are visible from the CLI (`--report`) and in the UI, from the same file — no second
  source of truth to drift.

State: **planned.**

## 4. All data available from the web
> "All data needs to be available from the web."

**What that rules out.** Any fact that only exists in a terminal: a `journalctl` line, a log file nobody
opens, a `cat` in a chat. If it is not in the panel, it does not exist for the person deciding.

**What is missing today.** The Cycles panel shows restarts and who was interrupted. Everything else
about the same process lives elsewhere: the audit of each run, the resume attempts and their outcome,
the timings per phase, and the ledger's own generation time. Worse, part of what happened during the
first two attempts exists *only* in `journalctl -u p4-restart-*` — the web cannot read the journal at
all, so that data is invisible by construction.

**Therefore:** the scripts write everything to append-only files, and the backend serves those files.
The journal stays a debugging convenience, never the record. Concretely, the panel must show, from the
same data the CLI prints: each restart (when, what asked for it, what it stopped, what it resumed, what
it lost, how long each phase took), the audit line for every session it touched, and the states it
could not determine — with the refresh the host already provides.

**State:** planned. The panel today shows the first slice (restarts and interrupted sessions).

## 5. The table must survive a phone
> "You need to figure out how to correctly render data in a table that looks good on mobile. Current
> cycles table has cells that use a bit of all the space while other cells make the row height grow
> disproportionately."

**What is wrong today.** The Cycles table is a browser-default table with five equal-ish columns:
* the numeric columns (working / resumed / interrupted) take as much width as the text column, and are
  centred in it, so three digits float in a wide empty cell;
* the last column renders the whole list of lost agents inline, so one bad restart makes the row ten
  lines tall and the numbers beside it become a column of whitespace;
* on a 390 px phone, the five columns squeeze the only text that matters into a sliver.

**What it should be.**
* numbers: narrow, right-aligned, `white-space: nowrap`, `width: 1%` — they must never take space from text;
* the list of lost agents: not inline. Show the count plus at most two entries, with "and N more"
  expanding on demand (`<details>` needs no JavaScript and stays accessible);
* below a breakpoint, stop being a table: one card per restart, with the date and the counts as chips on
  one line, and the agents listed under it. A table that cannot fit is not made to fit by shrinking text;
* row height driven by *content that is actually shown*, never by content that is collapsed;
* the same treatment applies to the likes table (it already has a column picker, but the same
  equal-width problem exists there).

State: planned.

## 6. Times in the user's time zone
> "Forgot, time in user time zone."

**Two offenders today.**
* The Cycles panel prints `2026-10-30T04:41:57+00:00` sliced to 16 characters — that is **UTC**, labelled
  as if it were local. A restart at 23:41 in Bogotá reads as 04:41.
* The likes table hardcodes `America/Bogota` in the browser. Right for one user, wrong for anyone else,
  and wrong again if the machine's zone ever changes.

**The rule.** Store UTC (unambiguous, sortable), render in the viewer's zone. In the browser that is
`new Date(iso).toLocaleString(undefined, {...})` — no zone constant, no slicing of ISO strings. In the
CLI it is `astimezone()` with the system zone. A time without its zone is a bug, and a hardcoded zone
is the same bug wearing a disguise.

State: planned (small, do it with the mobile table since both are in the same render code).

## Progress log

* **Item 1, foundation — built and tested.** `activity/activity.js` (Pi extension) publishes
  `<cwd>/.pi-web/agent_activity.jsonl`: `session_start`, `turn_start`, `message_start/end`,
  `tool_start/end`, `turn_end`, `session_shutdown`, each stamped **with the local offset**
  (`2026-10-30T00:01:07.247-05:00`, item 6 done here for free).
  Tested for real: `pi -p -e activity/activity.js` produced 10 ordered events for one turn, so
  "busy" (`turn_start` … `turn_end`) and "idle" are now observable from outside — which is what item 1
  was missing. Turn timings are visible in that test: 5.03 s between user message and assistant start
  (model latency), 8 ms for the answer.
  **Not yet wired:** the orchestrator still waits on transcript mtimes; switching it to this state is
  the next step.
