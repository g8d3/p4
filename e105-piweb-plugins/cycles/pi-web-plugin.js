// p4.cycles — what each session-daemon restart interrupted, in the selected workspace.
//
// Render stays synchronous: the last fetch is cached and the host is asked to re-render
// when a new one lands (the idiom the bundled panels use). The data comes from the paired
// server entry, which reads .pi-web/agent_cycles.json written by scripts/cycles.py.
//
// Read-only on purpose: resuming an interrupted agent is a dispatch, and that belongs to a
// Pi extension (docs/agent-cycles.md). A panel that claims to resume would be lying.
const CACHE = new Map();

const STYLE = `
.p4cy{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;gap:10px;padding:12px;overflow:auto}
.p4cy h2{margin:0;font-size:1rem}
.p4cy .sub{margin:0;color:var(--pi-muted);font-size:.88rem}
.p4cy table{width:100%;border-collapse:collapse;font-size:.88rem}
.p4cy th{text-align:left;position:sticky;top:0;background:var(--pi-surface,transparent);padding:8px;
  font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--pi-muted);
  border-bottom:1px solid var(--pi-border-muted)}
.p4cy td{padding:8px;border-bottom:1px solid var(--pi-border-muted);vertical-align:top}
.p4cy .when{font-family:ui-monospace,monospace;font-size:.8rem;white-space:nowrap}
.p4cy .bad{color:var(--pi-warning,#ffd479);font-weight:600}
.p4cy .ok{color:var(--pi-success,#8ee6a8)}
.p4cy ul{margin:4px 0 0 14px;padding:0;color:var(--pi-muted);font-size:.82rem}
.p4cy li{overflow-wrap:anywhere}
.p4cy .foot{color:var(--pi-muted);font-size:.8rem}
.p4cy .empty{color:var(--pi-muted);padding:14px 0;line-height:1.5}
.p4cy code{font-family:ui-monospace,monospace;font-size:.85em}
.p4cy .tools button{font:inherit;padding:6px 11px;border-radius:8px;border:1px solid var(--pi-border-muted);
  background:transparent;color:inherit;cursor:pointer}
`;

const fmt = (iso) => (iso || "").replace("T", " ").slice(0, 16);

function keyOf(context) {
  const w = context.workspace || {};
  return (context.machine && context.machine.id ? context.machine.id : "") + "|" + (w.path || "");
}

function fetchInto(context) {
  const key = keyOf(context);
  const entry = CACHE.get(key) || { data: null, fetching: false, error: null, at: 0 };
  CACHE.set(key, entry);
  if (entry.fetching) return;
  if (!context.peer || !context.peer.request) {
    entry.error = "This machine has no backend for the package: enable the plugin and restart the session daemon.";
    return;
  }
  entry.fetching = true;
  context.peer.request("cycles", null)
    .then((res) => {
      entry.data = res && typeof res === "object" ? { ...res, cycles: res.cycles || [] } : null;
      entry.error = entry.data && entry.data.ok === false && !entry.data.missing
        ? (entry.data.error || "could not read the ledger") : null;
      entry.at = Date.now();
    })
    .catch((err) => { entry.error = String((err && err.message) || err); })
    .finally(() => {
      entry.fetching = false;
      try { context.host.requestRender(); } catch (e) { /* tab closed */ }
    });
}

function listInterrupted(html, c) {
  if (!c.interrupted || !c.interrupted.length) return html`<span class="ok">nothing lost</span>`;
  return html`<ul>${c.interrupted.map((w) => html`<li>${(w.title || w.id || "").slice(0, 90)}
    <span class="foot"> · last write ${fmt(w.last).slice(11)}</span></li>`)}</ul>`;
}

function view(html, context, entry) {
  const data = entry.data;
  const cycles = (data && data.cycles) || [];
  const lost = cycles.reduce((n, c) => n + ((c.interrupted || []).length), 0);
  return html`
    <style>${STYLE}</style>
    <div class="p4cy">
      <section>
        <h2>Agent cycles <span class="foot">${data && data.since ? html`· last ${data.since}` : null}</span></h2>
        <p class="sub">
          ${data && data.ok !== false
            ? html`${cycles.length} restart(s) interrupted work · ${lost} agent(s) never wrote again ·
                   ledger built ${fmt(data.generated_at)}`
            : html`Waiting for the ledger.`}
        </p>
      </section>

      ${entry.error ? html`<p class="empty">${entry.error}</p>` : null}

      ${!entry.error && data && data.missing ? html`
        <p class="empty">
          No ledger in this workspace yet. It is written by
          <code>python3 e105-piweb-plugins/scripts/cycles.py</code> (timer <code>p4-agent-cycles</code>,
          every 15 minutes). Run it once here and this panel fills in.
        </p>` : null}

      ${!entry.error && !data ? html`<p class="empty">Loading the ledger…</p>` : null}

      ${!entry.error && data && data.ok !== false && cycles.length === 0 ? html`
        <p class="empty">No restart interrupted a session in this window.</p>` : null}

      ${cycles.length ? html`
        <table>
          <thead><tr><th>Restart</th><th>Working</th><th>Resumed</th><th>Interrupted</th><th>Who never wrote again</th></tr></thead>
          <tbody>${cycles.slice().reverse().map((c) => html`
            <tr>
              <td class="when">${fmt(c.boot)}</td>
              <td>${(c.working || []).length}</td>
              <td class="${(c.resumed || []).length ? "ok" : ""}">${(c.resumed || []).length}</td>
              <td class="${(c.interrupted || []).length ? "bad" : ""}">${(c.interrupted || []).length}</td>
              <td>${listInterrupted(html, c)}</td>
            </tr>`)}</tbody>
        </table>` : null}

      <p class="foot">
        Read-only. Resuming an interrupted agent is a dispatch, which belongs to a Pi extension
        (<code>docs/agent-cycles.md</code>); this panel reports, it does not resurrect.
        ${data && data.note ? html`<br>${data.note}` : null}
      </p>
    </div>`;
}

const plugin = {
  apiVersion: 4,
  name: "Agent cycles",
  activate: ({ html, svg }) => ({
    contributions: {
      workspacePanels: [
        {
          id: "p4.cycles.panel",
          title: "Cycles",
          order: 985,
          icon: svg`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-3-6.7"></path><path d="M21 3v6h-6"></path>
          </svg>`,
          render: (context) => {
            const entry = CACHE.get(keyOf(context)) || { data: null, error: null, fetching: false };
            if (!entry.data && !entry.fetching && !entry.error) fetchInto(context);
            if (entry.data && Date.now() - (entry.at || 0) > 60000) fetchInto(context);
            return view(html, context, entry);
          },
        },
      ],
    },
  }),
};

export default plugin;
