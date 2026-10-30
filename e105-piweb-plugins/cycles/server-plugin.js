// p4.cycles server entry: everything the panel shows comes from here, so the CLI and the UI read
// the same files. Read-only: nothing in this file restarts or resumes anything.
//
//   .pi-web/agent_cycles.json     restarts and the sessions they interrupted (scripts/cycles.py)
//   .pi-web/restart_audit.jsonl   one line per run: intent, phases, resumes, and whether they worked
//   ~/.pi-web/agent_activity.jsonl  machine-wide turn state written by the p4 activity extension
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const FILE = path.join(".pi-web", "agent_cycles.json");
const AUDIT = path.join(".pi-web", "restart_audit.jsonl");
const DATA = process.env.PI_WEB_DATA_DIR || path.join(os.homedir(), ".pi-web");
const BUSY = new Set(["turn_start", "message_start", "tool_start"]);
const IDLE = new Set(["turn_end", "session_shutdown"]);

// A workspace may be a worktree: the ledger belongs to the project, so resolve the main checkout.
function projectRoot(start) {
  let dir = path.resolve(start);
  for (let i = 0; i < 6; i += 1) {
    const dotGit = path.join(dir, ".git");
    try {
      const st = fs.statSync(dotGit);
      if (st.isDirectory()) return dir;
      if (st.isFile()) {
        const m = fs.readFileSync(dotGit, "utf8").trim().match(/^gitdir:\s*(.+)$/);
        if (m) {
          const common = path.resolve(dir, m[1].trim());
          const idx = common.indexOf(path.sep + ".git" + path.sep);
          if (idx > 0) return common.slice(0, idx);
        }
        return dir;
      }
    } catch { /* keep walking up */ }
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return path.resolve(start);
}

function firstExisting(paths) {
  return paths.find((p) => { try { return fs.existsSync(p); } catch { return false; } }) || paths[0];
}

function readJSON(file) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return null; }
}

function readJSONL(file, limit) {
  try {
    const rows = [];
    const lines = fs.readFileSync(file, "utf8").split("\n");
    // Only the tail matters: newest decisive event per session, newest audit runs.
    // Reading the whole file on every panel render is what made this grow without bound.
    const tail = lines.slice(-Math.max(1, limit));
    for (const line of tail) {
      const t = line.trim();
      if (!t) continue;
      try { rows.push(JSON.parse(t)); } catch { /* one bad line must not hide the rest */ }
    }
    return rows;
  } catch { return []; }
}

// The newest decisive event per session: the same rule the orchestrator uses.
// Bounded by design: the panel only shows the newest N sessions, so the backend
// only returns that many. Reading more lines than needed was the slow growth.
function activityBySession(file, lineLimit, sessionLimit) {
  const out = new Map();
  for (const row of readJSONL(file, lineLimit)) {
    const sid = row.session;
    if (!sid) continue;
    const ev = row.event || "";
    const decisive = BUSY.has(ev) || IDLE.has(ev);
    const prev = out.get(sid) || { state: "idle" };
    out.set(sid, {
      session: sid,
      cwd: row.cwd || "",
      state: decisive ? (BUSY.has(ev) ? "busy" : "idle") : prev.state,
      at: row.at || "",
      last: ev,
      title: prev.title || "",
    });
  }
  return [...out.values()].sort((a, b) => String(b.at).localeCompare(String(a.at))).slice(0, sessionLimit);
}

const DEFAULTS = { lines: 2000, audit: 10, cycles: 12, sessions: 30 };

function limitsFrom(input) {
  const p = (input && typeof input === "object") ? input : {};
  const num = (v, d) => (Number.isSafeInteger(v) && v > 0 ? Math.min(v, 500) : d);
  return {
    lines: num(p.lines, DEFAULTS.lines),
    auditLimit: num(p.auditLimit ?? p.audit, DEFAULTS.audit),
    cyclesLimit: num(p.cyclesLimit ?? p.cycles, DEFAULTS.cycles),
    sessionLimit: num(p.activityLimit ?? p.sessions, DEFAULTS.sessions),
  };
}

function read(workspacePath, input) {
  const lim = limitsFrom(input);
  const ws = path.resolve(workspacePath);
  const root = projectRoot(ws);
  const ledgerFile = firstExisting([path.join(ws, FILE), path.join(root, FILE)]);
  const auditFile = firstExisting([path.join(DATA, AUDIT), path.join(ws, AUDIT), path.join(root, AUDIT)]);
  const activityFile = path.join(DATA, "agent_activity.jsonl");

  const ledger = readJSON(ledgerFile) || {};
  const audit = readJSONL(auditFile, lim.lines).filter((r) => !r.intent).slice(-lim.auditLimit);
  const activity = activityBySession(activityFile, lim.lines, lim.sessionLimit);

  return {
    ok: Boolean(ledger.generated_at || audit.length || activity.length),
    generated_at: ledger.generated_at || null,
    since: ledger.since || "",
    boots: ledger.boots || 0,
    sessions_seen: ledger.sessions_seen || 0,
    windows: ledger.windows || {},
    note: ledger.note || "",
    cycles: Array.isArray(ledger.cycles) ? ledger.cycles.slice(-lim.cyclesLimit) : [],
    audit,
    activity,
    files: { ledger: ledgerFile, audit: auditFile, activity: activityFile },
    root,
    limits: lim,
  };
}

const plugin = {
  apiVersion: 3,
  name: "Agent cycles",
  activate() {
    return {
      peer: {
        async request(context) {
          if (context.signal && context.signal.aborted) throw new Error("aborted");
          const op = context.operation;
          if (op !== "state" && op !== "cycles") throw new Error("unknown operation: " + op);
          const data = read(context.workspace.path, context.input);
          // "cycles" stays for older panel builds: same payload, nothing removed
          return JSON.parse(JSON.stringify(data));
        },
      },
      health() { return { status: "healthy" }; },
    };
  },
};

export default plugin;
