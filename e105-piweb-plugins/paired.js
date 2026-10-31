// Shared transport for our browser-only panels.
//
// Why this file exists: a plugin entry with a serverModule pins its browser
// asset to the session daemon's *active* revision, so after any package update
// the browser is told to fetch an asset the daemon cannot serve yet (404) and
// the tab silently disappears until the daemon restarts — the restart that
// orphans every working agent. A browser-only entry (no serverModule) is
// served fresh on every page reload instead (p4.catalog proves it).
//
// So the panels live here as browser-only plugins and call the server-only
// backends (p4.cycles, p4.models) over plain HTTP through the host's
// paired-backend proxy, using the backend's *active* revision from /api/plugins.
// New panel code works against an old backend: unknown input fields are
// ignored there, and the panels slice and default everything client-side.
export async function backendRevision(pluginId) {
  let res;
  try {
    res = await fetch("/api/plugins");
  } catch (e) {
    throw new Error("PI WEB is unreachable: " + (e && e.message ? e.message : e));
  }
  if (!res.ok) throw new Error("plugin list unavailable (HTTP " + res.status + ")");
  const list = await res.json();
  const entry = ((list && list.plugins) || []).find((p) => p && p.id === pluginId);
  if (!entry) throw new Error("backend " + pluginId + " is not installed on this machine");
  const rev = entry.server && (entry.server.activeRevision || entry.server.desiredRevision);
  if (!rev) {
    throw new Error("backend " + pluginId + " has no active revision yet — it loads on the next session-daemon restart");
  }
  return rev;
}

export async function pairedRequest({ pluginId, operation, input, scope, projectId, workspaceId }) {
  const revision = await backendRevision(pluginId);
  const parts = ["api", "paired-plugin-backends", encodeURIComponent(pluginId)];
  if (projectId !== undefined) parts.push("projects", encodeURIComponent(projectId));
  if (workspaceId !== undefined) parts.push("workspaces", encodeURIComponent(workspaceId));
  parts.push(encodeURIComponent(operation));
  const url = "/" + parts.join("/");
  const body = { revision, input: input === undefined ? null : input };
  if (scope !== undefined) body.scope = scope;
  if (projectId !== undefined) body.projectId = projectId;
  if (workspaceId !== undefined) body.workspaceId = workspaceId;
  let res;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new Error("backend unreachable: " + (e && e.message ? e.message : e));
  }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* error body below */ }
  if (!res.ok) {
    const msg = (data && (data.error || data.message)) || ("HTTP " + res.status);
    throw new Error(msg);
  }
  return data;
}
