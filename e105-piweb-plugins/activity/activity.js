// p4 activity — tells the restart orchestrator what each agent is actually doing.
//
// The problem this solves: from outside, a session looks the same whether it is thinking, waiting on
// a model, running a tool, or finished. The only place that knows is inside the agent runtime, and a
// Pi extension is the supported way to listen there. So this writes the truth to
// <cwd>/.pi-web/agent_activity.jsonl (append-only), and the orchestrator waits on that state instead
// of on a stopwatch.
//
// One line per event: {"at": ISO-8601 with offset, "session", "cwd", "event", "detail"?}
// States the orchestrator cares about: turn_start (busy) ... turn_end (idle). Anything else is context.
import { appendFileSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const OFF = process.env.P4_ACTIVITY === "0";

function sessionIdOf(ctx) {
  try {
    const sm = ctx && ctx.sessionManager;
    // Called as a method on purpose: the implementation reads `this.sessionId`.
    if (sm && typeof sm.getSessionId === "function") return sm.getSessionId() || "";
  } catch {
    /* older host: fall through */
  }
  return "";
}

function stamp() {
  // Local offset included on purpose: a bare UTC time is what read as "04:41" for a 23:41 restart.
  const d = new Date();
  const pad = (n, w = 2) => String(Math.abs(n)).padStart(w, "0");
  const off = -d.getTimezoneOffset();
  const sign = off >= 0 ? "+" : "-";
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}.${pad(d.getMilliseconds(), 3)}` +
    `${sign}${pad(Math.trunc(Math.abs(off) / 60))}:${pad(Math.abs(off) % 60)}`
  );
}

// MACHINE-wide on purpose: a daemon restart interrupts every session on the machine, so the
// orchestrator needs one file that lists all of them. A per-workspace file made "who is busy?"
// a question about the wrong scope (2026-10-30: a restart was planned for one workspace and
// killed sessions in every other one).
const GLOBAL_FILE = join(process.env.PI_WEB_DATA_DIR || join(homedir(), ".pi-web"), "agent_activity.jsonl");

function log(cwd, session, event, detail) {
  if (OFF) return;
  const line = JSON.stringify({ at: stamp(), session, cwd, event, ...(detail ? { detail } : {}) }) + "\n";
  try {
    mkdirSync(join(GLOBAL_FILE, ".."), { recursive: true });
    appendFileSync(GLOBAL_FILE, line);
  } catch {
    /* never break the agent because a log line failed */
  }
  // the workspace copy stays for anything that inspects a single workspace
  if (!cwd) return;
  try {
    const dir = join(cwd, ".pi-web");
    mkdirSync(dir, { recursive: true });
    appendFileSync(join(dir, "agent_activity.jsonl"), line);
  } catch {
    /* same */
  }
}

export default function p4Activity(pi) {
  const emit = (event, ctx, detail) => log(ctx && ctx.cwd, sessionIdOf(ctx), event, detail);

  pi.on("session_start", (event, ctx) => emit("session_start", ctx, { reason: event && event.reason }));
  pi.on("turn_start", (event, ctx) => emit("turn_start", ctx));
  pi.on("turn_end", (event, ctx) => emit("turn_end", ctx));
  pi.on("message_start", (event, ctx) =>
    emit("message_start", ctx, { role: event && event.message && event.message.role }));
  pi.on("message_end", (event, ctx) =>
    emit("message_end", ctx, { role: event && event.message && event.message.role }));
  pi.on("tool_execution_start", (event, ctx) =>
    emit("tool_start", ctx, { tool: event && event.toolName }));
  pi.on("tool_execution_end", (event, ctx) =>
    emit("tool_end", ctx, { tool: event && event.toolName, ok: !(event && event.error) }));
  pi.on("session_shutdown", (event, ctx) => emit("session_shutdown", ctx));
}
