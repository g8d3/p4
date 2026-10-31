// p4.models.panel — browser-only panel for the model-list guard backend.
//
// This entry has NO serverModule on purpose (see cycles/panel.js): the panel
// hot-reloads on page refresh and calls the server-only p4.models backend
// over plain HTTP (see ../paired.js) using the backend's active revision.
// No session-daemon restart needed to see new panel code.
import { pairedRequest } from "../paired.js";
import { WANTED } from "./wanted-public.js";
// The guard behind this panel: whether your picks are still in pi's enabledModels list,
//
// Something rewrites ~/.pi/agent/settings.json on some restarts and the list comes back wrong
// (2026-10-30: 107 models became 3 after `pi install`; later the old guard itself rewrote a
// deliberate 4-model edit back to 162). A missing pick is put back automatically and logged here;
// anything extra is left alone, and this panel says so. Picks live in wanted.json — see
// docs/current-models.md.
const CACHE = { data: null, fetching: false, error: null, at: 0 };
const REFRESH_MS = 30000;

const STYLE = `
.p4m{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;gap:14px;padding:14px;overflow:auto}
.p4m h2{margin:0;font-size:1rem}
.p4m h3{margin:0 0 6px;font-size:.82rem;text-transform:uppercase;letter-spacing:.05em;color:var(--pi-muted)}
.p4m .sub{margin:0;color:var(--pi-muted);font-size:.85rem;line-height:1.45}
.p4m .cards{display:grid;gap:10px}
.p4m .card{border:1px solid var(--pi-border-muted);border-radius:10px;padding:10px 12px;display:flex;flex-direction:column;gap:6px;min-width:0}
.p4m .card.bad{border-color:var(--pi-warning,#ffd479)}
.p4m .head{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;justify-content:space-between}
.p4m .when{font-variant-numeric:tabular-nums;font-weight:600;font-size:.9rem}
.p4m .chip{font-size:.75rem;padding:1px 8px;border-radius:99px;border:1px solid var(--pi-border-muted);color:var(--pi-muted);white-space:nowrap}
.p4m .chip.ok{color:var(--pi-success,#8ee6a8)}
.p4m .chip.bad{color:var(--pi-warning,#ffd479);font-weight:600}
.p4m .row{display:flex;gap:6px;font-size:.84rem;min-width:0}
.p4m .k{color:var(--pi-muted);flex:0 0 auto}
.p4m .v{min-width:0;overflow-wrap:anywhere}
.p4m ul{margin:6px 0 0 16px;padding:0;font-size:.82rem;color:var(--pi-muted)}
.p4m code{font-family:ui-monospace,monospace;font-size:.85em}
.p4m .empty{color:var(--pi-muted);font-size:.86rem}
@media (min-width:760px){ .p4m .cards{grid-template-columns:repeat(auto-fill,minmax(340px,1fr))} }
`;

const time = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? String(iso) : d.toLocaleString(undefined,
    { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
};

function view(html, entry) {
  const d = entry.data;
  const events = (d && d.events) || [];
  // Picks come from the backend when it knows them (after the daemon restart
  // that loads the new guard); until then this generated copy speaks for them.
  const backendKnowsPicks = Boolean(d && d.wanted);
  const picks = backendKnowsPicks ? d.wanted : (WANTED.models || []);
  const wantedCount = backendKnowsPicks ? (d.wantedCount ?? d.canonicalCount ?? picks.length) : picks.length;
  const savedAt = backendKnowsPicks ? (d.wantedSavedAt ?? d.savedAt) : (WANTED.savedAt || null);
  // Missing picks, computed here so the panel is exact even against the old
  // backend (which reports the enabled list but knows no picks).
  const enabled = (d && d.models) || [];
  const missing = (d && d.missing) || picks.filter((m) => !enabled.includes(m));
  const healthy = d && missing.length === 0;
  return html`
    <style>${STYLE}</style>
    <div class="p4m">
      <section>
        <h2>Model list</h2>
        <p class="sub">
          ${d ? html`${d.count} models enabled · ${wantedCount} picks · saved ${time(savedAt)}`
               : html`Reading the settings file…`}
        </p>
      </section>

      ${entry.error ? html`<p class="empty">${entry.error}</p>` : null}

      ${d ? html`
        <section>
          <div class="cards">
            <div class="card ${healthy ? "" : "bad"}">
              <div class="head">
                <span class="when">${d.count} enabled</span>
                <span class="chip ${healthy ? "ok" : "bad"}">${healthy ? "all picks present" : `${missing.length} pick(s) missing`}</span>
              </div>
              <div class="row"><span class="k">file</span><span class="v"><code>${d.settings}</code></span></div>
              <div class="row"><span class="k">picks</span><span class="v"><code>${d.wantedFile || "wanted.json"}</code></span></div>
              <div class="row"><span class="k">default</span><span class="v">${d.defaultProvider || "—"} / ${d.defaultModel || "—"}</span></div>
              ${d.backend ? html`<div class="row"><span class="k">backend</span><span class="v">pid ${d.backend.pid} · up since ${time(d.backend.startedAt)}</span></div>` : ""}
              <div class="row"><span class="k">repair rule</span><span class="v">a missing pick is put back;
                anything extra is left alone; the picks file is never rewritten by the guard —
                change picks there, not in the picker</span></div>
              ${missing.length ? html`<div class="row"><span class="k">missing</span><span class="v">${missing.map((m) => html`<code>${m}</code> `)}</span></div>` : null}
            </div>
          </div>
        </section>` : null}

      <section>
        <h3>Repairs and drift</h3>
        ${events.length ? html`
          <div class="cards">${events.map((e) => html`
            <div class="card ${e.event === "repaired" ? "bad" : ""}">
              <div class="head">
                <span class="when">${time(e.at)}</span>
                <span class="chip ${e.event === "repaired" ? "bad" : "ok"}">${e.event}</span>
              </div>
              ${e.had !== undefined ? html`<div class="row"><span class="k">had</span><span class="v">${e.had} models →
                restored to ${e.restoredTo}</span></div>` : null}
              ${e.backup ? html`<div class="row"><span class="k">backup</span><span class="v"><code>${e.backup}</code></span></div>` : null}
            </div>`)}</div>`
          : html`<p class="empty">No repair needed since the picks were recorded. That is the good case.</p>`}
      </section>

      ${picks.length ? html`
        <details open>
          <summary class="sub">Your ${picks.length} picks${backendKnowsPicks ? "" : " (from your saved shortlist — backend update pending)"}</summary>
          <ul>${picks.map((m) => html`<li><code>${m}</code>${enabled.length && !enabled.includes(m) ? " — missing, will be put back" : ""}</li>`)}</ul>
        </details>` : null}

      <p class="sub">
        The guard puts back missing picks; it does not patch pi or PI WEB. If the file is
        rewritten again, the repair is logged here with a backup of what was there before.
      </p>
    </div>`;
}

async function scopeOf(w) {
  if (w.projectId && w.id) return w;
  const pr = await (await fetch("/api/projects")).json();
  for (const p of pr.projects || pr || []) {
    const pid = p.id || p.projectId;
    if (!pid) continue;
    try {
      const wr = await (await fetch(`/api/projects/${encodeURIComponent(pid)}/workspaces`)).json();
      const ws = wr.workspaces || [];
      if (ws.length) return { projectId: pid, id: ws[0].id };
    } catch { /* try the next project */ }
  }
  throw new Error("No workspace exists yet — create one to read the guard.");
}

function fetchInto(context) {
  if (CACHE.fetching) return;
  // The guard is machine-global, but API v3 backends require workspace scope:
  // any selected workspace routes the call, the data does not depend on it.
  // With no workspace selected (fresh page), discover one via the API instead
  // of showing a dead tab — values come from the server, never hardcoded.
  const w = context.workspace || context.selectedWorkspace || {};
  CACHE.fetching = true;
  CACHE.error = null;
  scopeOf(w).then((s) => pairedRequest({
    pluginId: "p4.models",
    operation: "models",
    input: null,
    scope: "workspace",
    projectId: s.projectId,
    workspaceId: s.id,
  }))
    .then((res) => { CACHE.data = res || null; CACHE.error = null; CACHE.at = Date.now(); })
    .catch((err) => {
      const s = String((err && err.message) || err || "");
      CACHE.error = /stale-plugin-revision|inactive-plugin|restart|stale|missing|not active/i.test(s)
        ? ("New version installed — restart the session daemon, then reload this page. " +
           "Your data is safe; the tab shows again after the restart.")
        : s;
    })
    .finally(() => {
      CACHE.fetching = false;
      try { context.host.requestRender(); } catch { /* closed */ }
    });
}

const plugin = {
  apiVersion: 4,
  name: "Model list guard",
  activate: ({ html, svg }) => ({
    contributions: {
      applicationPanels: [
        {
          id: "p4.models.panel",
          title: "Models",
          order: 990,
          icon: svg`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 7h16M4 12h10M4 17h7"></path><circle cx="18" cy="16" r="3"></circle>
          </svg>`,
          render: (context) => {
            if ((!CACHE.data && !CACHE.fetching && !CACHE.error) || (CACHE.at && Date.now() - CACHE.at > REFRESH_MS)) {
              fetchInto(context);
            }
            return view(html, CACHE);
          },
        },
      ],
    },
  }),
};

export default plugin;
