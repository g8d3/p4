// p4.cycles server entry: serves the cycles ledger of the selected workspace.
//
// Reads <workspace>/.pi-web/agent_cycles.json, which scripts/cycles.py writes every 15
// minutes (systemd: p4-agent-cycles.timer). Read-only: nothing here resumes an agent.
import fs from "node:fs";
import path from "node:path";

const FILE = path.join(".pi-web", "agent_cycles.json");

// Worktrees are the normal case here: a workspace may be p4/e092-crew-puerto while the
// project root is p4/. The ledger belongs to the project, so a worktree resolves to its
// main checkout before the file is looked up (a worktree's .git is a file pointing at it).
function projectRoot(start) {
  let dir = path.resolve(start);
  for (let i = 0; i < 6; i += 1) {
    const dotGit = path.join(dir, ".git");
    try {
      const st = fs.statSync(dotGit);
      if (st.isDirectory()) return dir;              // main checkout
      if (st.isFile()) {                             // worktree: "gitdir: <main>/.git/worktrees/<name>"
        const line = fs.readFileSync(dotGit, "utf8").trim();
        const m = line.match(/^gitdir:\s*(.+)$/);
        if (m) {
          const common = path.resolve(dir, m[1].trim());
          const idx = common.indexOf(path.sep + ".git" + path.sep);
          if (idx > 0) return common.slice(0, idx);
        }
        return dir;
      }
    } catch (e) { /* keep walking up */ }
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return path.resolve(start);
}

function ledgerPaths(workspacePath) {
  const ws = path.resolve(workspacePath);
  const root = projectRoot(ws);
  const seen = [...new Set([path.join(ws, FILE), path.join(root, FILE)])];
  return { root, candidates: seen };
}

function read(workspacePath) {
  const { root, candidates } = ledgerPaths(workspacePath);
  const file = candidates.find((f) => fs.existsSync(f)) || candidates[0];
  try {
    const data = JSON.parse(fs.readFileSync(file, "utf8"));
    return {
      ok: true,
      generated_at: data.generated_at || null,
      since: data.since || "",
      boots: data.boots || 0,
      sessions_seen: data.sessions_seen || 0,
      windows: data.windows || {},
      note: data.note || "",
      root,
      file,
      cycles: Array.isArray(data.cycles) ? data.cycles : [],
    };
  } catch (error) {
    // A missing ledger is not an error: it means the script has not run in this workspace.
    return {
      ok: false,
      missing: error && error.code === "ENOENT",
      error: String((error && error.message) || error),
      file,
      root,
      cycles: [],
    };
  }
}

const plugin = {
  apiVersion: 3,
  name: "Agent cycles",
  activate() {
    return {
      peer: {
        async request(context) {
          if (context.signal && context.signal.aborted) throw new Error("aborted");
          if (context.operation !== "cycles") throw new Error("unknown operation: " + context.operation);
          const root = context.workspace.path;
          return JSON.parse(JSON.stringify(read(root)));
        },
      },
      health() {
        return { status: "healthy" };
      },
    };
  },
};

export default plugin;
