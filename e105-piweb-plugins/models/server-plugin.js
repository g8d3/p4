// p4.models server entry: runs the guard inside the session daemon, so enabledModels is protected
// without installing anything into pi and without patching PI WEB core.
import { report, startGuard } from "./models.js";

const plugin = {
  apiVersion: 3,
  name: "Model list guard",
  activate() {
    const stop = startGuard();
    return {
      peer: {
        async request(context) {
          if (context.operation !== "models") throw new Error("unknown operation: " + context.operation);
          return JSON.parse(JSON.stringify(report()));
        },
      },
      health() { return { status: "healthy" }; },
      dispose() { try { stop(); } catch { /* ignore */ } },
    };
  },
};

export default plugin;
