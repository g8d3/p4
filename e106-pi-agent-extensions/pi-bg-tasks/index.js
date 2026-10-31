/**
 * pi-bg-tasks — non-blocking background shell tasks as first-class tools.
 *
 * Why a plugin, not a wrapper script: tools registered here show up in the
 * system prompt (promptSnippet + promptGuidelines), so every session knows
 * them without reading any docs. A slow command goes through bg_start and
 * returns in milliseconds; output is collected later with bg_tail/bg_wait.
 * The registry is file-based (~/.pi/agent/bg-tasks/), so tasks are visible
 * across sessions and survive daemon restarts (children are fully detached).
 */
import { spawn } from "node:child_process";
import {
  appendFileSync,
  mkdirSync,
  openSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { Type } from "typebox";

const DIR = join(homedir(), ".pi", "agent", "bg-tasks");
const ID_RE = /^[a-z0-9][a-z0-9-_]{0,63}$/i;

const ok = (text, details) => ({ content: [{ type: "text", text }], details });
const err = (text) => ({ content: [{ type: "text", text }], isError: true });

function dir() {
  mkdirSync(DIR, { recursive: true });
  return DIR;
}
function pathOf(id) {
  return join(dir(), `${id}.json`);
}
function load(id) {
  try {
    return JSON.parse(readFileSync(pathOf(id), "utf8"));
  } catch {
    return null;
  }
}
function save(entry) {
  writeFileSync(pathOf(entry.id), JSON.stringify(entry, null, 2) + "\n");
}
function alive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}
/** Refresh a registry entry against reality; returns the entry. */
function refresh(entry) {
  if (!entry || entry.status !== "running") return entry;
  if (alive(entry.pid)) return entry;
  entry.status = "done";
  entry.endedAt = new Date().toISOString();
  save(entry);
  return entry;
}
function newId() {
  return `t${Date.now().toString(36)}${Math.floor(Math.random() * 0xffff).toString(36)}`;
}
function summary(e) {
  return `${e.id}: ${e.status}${e.exitCode !== undefined && e.exitCode !== null ? ` (exit ${e.exitCode})` : ""} pid=${e.pid} log=${e.log}`;
}

export default function bgTasksExtension(pi) {
  pi.registerTool({
    name: "bg_start",
    label: "Background task start",
    description:
      "Start a shell command fully detached and return immediately with a task id. Use for anything expected past ~5s instead of blocking the turn.",
    promptSnippet: "Background shell tasks: bg_start / bg_status / bg_tail / bg_wait / bg_kill.",
    promptGuidelines: [
      "Commands expected past ~5s go through bg_start and return in milliseconds; never block the turn on slow commands.",
      "Collect output later with bg_tail (peek) or bg_wait (bounded block), and kill strays with bg_kill.",
    ],
    parameters: Type.Object({
      cmd: Type.String({ description: "Executable, e.g. /bin/bash or python3" }),
      args: Type.Optional(Type.Array(Type.String(), { description: "Arguments" })),
      cwd: Type.Optional(Type.String({ description: "Working directory (default: current)" })),
      taskId: Type.Optional(
        Type.String({ description: "Short id [a-z0-9-_]; generated when omitted" }),
      ),
      log: Type.Optional(Type.String({ description: "Log file path; default ~/.pi/agent/bg-tasks/<id>.log" })),
    }),
    async execute(_id, params) {
      try {
        const id = params.taskId || newId();
        if (!ID_RE.test(id)) throw new Error(`Invalid task id ${JSON.stringify(id)}`);
        if (load(id) && refresh(load(id)).status === "running")
          throw new Error(`Task ${id} is already running`);
        const log = params.log || join(dir(), `${id}.log`);
        mkdirSync(dirname(log), { recursive: true });
        appendFileSync(log, "");
        const outFd = openSync(log, "a");
        const child = spawn(params.cmd, params.args ?? [], {
          cwd: params.cwd,
          detached: true,
          stdio: ["ignore", outFd, outFd],
        });
        child.unref();
        const entry = {
          id,
          cmd: params.cmd,
          args: params.args ?? [],
          cwd: params.cwd || process.cwd(),
          log,
          pid: child.pid ?? -1,
          startedAt: new Date().toISOString(),
          status: "running",
          exitCode: null,
          endedAt: null,
        };
        save(entry);
        child.on("error", () => {});
        child.on("exit", (code) => {
          const cur = load(id);
          if (!cur) return;
          cur.status = "done";
          cur.exitCode = code;
          cur.endedAt = new Date().toISOString();
          save(cur);
        });
        return ok(`Started ${id} (pid ${entry.pid}, log ${log}). Collect with bg_tail/bg_wait.`, {
          taskId: id,
          pid: entry.pid,
          log,
        });
      } catch (e) {
        return err(e.message);
      }
    },
  });

  pi.registerTool({
    name: "bg_status",
    label: "Background task status",
    description: "List background tasks (or one task) with live running/done state.",
    parameters: Type.Object({
      taskId: Type.Optional(Type.String({ description: "Single task id; omit for all" })),
    }),
    async execute(_id, params) {
      try {
        if (params.taskId) {
          const e = refresh(load(params.taskId));
          if (!e) throw new Error(`Unknown task ${params.taskId}`);
          return ok(summary(e), { task: e });
        }
        const all = readdirSync(dir())
          .filter((f) => f.endsWith(".json"))
          .map((f) => {
            try {
              return refresh(JSON.parse(readFileSync(join(dir(), f), "utf8")));
            } catch {
              return null;
            }
          })
          .filter(Boolean)
          .sort((a, b) => (a.startedAt < b.startedAt ? -1 : 1));
        if (!all.length) return ok("No background tasks.", { tasks: [] });
        return ok(all.map(summary).join("\n"), { tasks: all });
      } catch (e) {
        return err(e.message);
      }
    },
  });

  pi.registerTool({
    name: "bg_tail",
    label: "Background task log tail",
    description: "Read the last N lines of a background task's log without blocking.",
    parameters: Type.Object({
      taskId: Type.String({ description: "Task id" }),
      lines: Type.Optional(Type.Number({ description: "Lines from the end (default 20)" })),
    }),
    async execute(_id, params) {
      try {
        const e = refresh(load(params.taskId));
        if (!e) throw new Error(`Unknown task ${params.taskId}`);
        const n = Math.min(200, Math.max(1, Math.floor(params.lines ?? 20)));
        let text = "";
        try {
          const all = readFileSync(e.log, "utf8").split("\n");
          while (all.length && all[all.length - 1] === "") all.pop();
          text = all.slice(-n).join("\n") || "(log empty so far)";
        } catch {
          text = "(no log yet)";
        }
        return ok(`[${e.id} ${e.status}]\n${text}`, { taskId: e.id, status: e.status });
      } catch (e) {
        return err(e.message);
      }
    },
  });

  pi.registerTool({
    name: "bg_wait",
    label: "Background task wait",
    description:
      "Block (bounded) until a background task finishes or the timeout hits. For scripts and true synchronization points; sessions should prefer doing other work and checking bg_status/bg_tail at breakpoints.",
    parameters: Type.Object({
      taskId: Type.String({ description: "Task id" }),
      timeoutSec: Type.Optional(Type.Number({ description: "Max seconds to wait (default 300)" })),
    }),
    async execute(_id, params) {
      try {
        let e = refresh(load(params.taskId));
        if (!e) throw new Error(`Unknown task ${params.taskId}`);
        const deadline = Date.now() + Math.min(3600, Math.max(1, params.timeoutSec ?? 300)) * 1000;
        while (e.status === "running" && Date.now() < deadline) {
          await new Promise((r) => setTimeout(r, 500));
          e = refresh(load(params.taskId));
        }
        return ok(
          e.status === "running"
            ? `${e.id} still running after timeout (log ${e.log})`
            : `${e.id} ${e.status} (exit ${e.exitCode}) — log ${e.log}`,
          { taskId: e.id, status: e.status },
        );
      } catch (e) {
        return err(e.message);
      }
    },
  });

  pi.registerTool({
    name: "bg_kill",
    label: "Background task kill",
    description: "Terminate a running background task (TERM, then KILL if needed).",
    parameters: Type.Object({
      taskId: Type.String({ description: "Task id" }),
    }),
    async execute(_id, params) {
      try {
        const e = refresh(load(params.taskId));
        if (!e) throw new Error(`Unknown task ${params.taskId}`);
        if (e.status !== "running") return ok(`${e.id} already ${e.status}.`, { taskId: e.id });
        try {
          process.kill(e.pid, "SIGTERM");
        } catch {}
        await new Promise((r) => setTimeout(r, 1000));
        if (alive(e.pid)) {
          try {
            process.kill(e.pid, "SIGKILL");
          } catch {}
          await new Promise((r) => setTimeout(r, 500));
        }
        e.status = alive(e.pid) ? "running" : "killed";
        e.endedAt = new Date().toISOString();
        save(e);
        return ok(
          e.status === "killed" ? `${e.id} killed.` : `${e.id} still alive (pid ${e.pid}).`,
          { taskId: e.id, status: e.status },
        );
      } catch (e) {
        return err(e.message);
      }
    },
  });
}
