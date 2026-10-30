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
    for (const line of fs.readFileSync(file, "utf8").split("\n")) {
      const t = line.trim();
      if (!t) continue;
      try { rows.push(JSON.parse(t)); } catch { /* one bad line must not hide the rest */ }
    }
    return rows.slice(-limit);
  } catch { return []; }
}

// The newest decisive event per session: the same rule the orchestrator uses.
function activityBySession(file) {
  const out = new Map();
  for (const row of readJSONL(file, 5000)) {
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
  return [...out.values()].sort((a, b) => String(b.at).localeCompare(String(a.at)));
}

function read(workspacePath) {
  const ws = path.resolve(workspacePath);
  const root = projectRoot(ws);
  const ledgerFile = firstExisting([path.join(ws, FILE), path.join(root, FILE)]);
  const auditFile = firstExisting([path.join(DATA, AUDIT), path.join(ws, AUDIT), path.join(root, AUDIT)]);
  const activityFile = path.join(DATA, "agent_activity.jsonl");

  const ledger = readJSON(ledgerFile) || {};
  const audit = readJSONL(auditFile, 40).filter((r) => !r.intent);
  const activity = activityBySession(activityFile);

  return {
    ok: Boolean(ledger.generated_at || audit.length || activity.length),
    generated_at: ledger.generated_at || null,
    since: ledger.since || "",
    boots: ledger.boots || 0,
    sessions_seen: ledger.sessions_seen || 0,
    windows: ledger.windows || {},
    note: ledger.note || "",
    cycles: Array.isArray(ledger.cycles) ? ledger.cycles : [],
    audit,
    activity,
    files: { ledger: ledgerFile, audit: auditFile, activity: activityFile },
    root,
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
          const data = read(context.workspace.path);
          // "cycles" stays for older panel builds: same payload, nothing removed
          return JSON.parse(JSON.stringify(data));
        },
      },
      health() { return { status: "healthy" }; },
    };
  },
};

export default plugin;
