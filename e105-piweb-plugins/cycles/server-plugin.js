// p4.cycles server entry: serves the cycles ledger of the selected workspace.
//
// Reads <workspace>/.pi-web/agent_cycles.json, which scripts/cycles.py writes every 15
// minutes (systemd: p4-agent-cycles.timer). Read-only: nothing here resumes an agent.
import fs from "node:fs";
import path from "node:path";

const FILE = path.join(".pi-web", "agent_cycles.json");

function read(root) {
  const file = path.join(root, FILE);
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
      cycles: Array.isArray(data.cycles) ? data.cycles : [],
    };
  } catch (error) {
    // A missing ledger is not an error: it means the script has not run in this workspace.
    return {
      ok: false,
      missing: error && error.code === "ENOENT",
      error: String((error && error.message) || error),
      file: file,
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
