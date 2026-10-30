// p4.models — whether pi's enabledModels list is intact, and every time it had to be repaired.
//
// The bug it watches for: something rewrites ~/.pi/agent/settings.json and collapses the list
// (2026-10-30: 107 models became 3). A collapse is repaired automatically and logged here; a
// deliberate removal of a model or two is not touched, and this panel says so.
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
  const healthy = d && d.count >= d.canonicalCount;
  return html`
    <style>${STYLE}</style>
    <div class="p4m">
      <section>
        <h2>Model list</h2>
        <p class="sub">
          ${d ? html`${d.count} models enabled · ${d.canonicalCount} known good · snapshot ${time(d.savedAt)}`
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
                <span class="chip ${healthy ? "ok" : "bad"}">${healthy ? "intact" : `${d.drop} missing`}</span>
              </div>
              <div class="row"><span class="k">file</span><span class="v"><code>${d.settings}</code></span></div>
              <div class="row"><span class="k">default</span><span class="v">${d.defaultProvider || "—"} / ${d.defaultModel || "—"}</span></div>
              <div class="row"><span class="k">repair rule</span><span class="v">a drop of ${d.minDrop}+ models that is a
                subset of the snapshot is repaired; removing one or two by hand is left alone</span></div>
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
          : html`<p class="empty">No repair needed since the snapshot was taken. That is the good case.</p>`}
      </section>

      ${d && d.models && d.models.length ? html`
        <details>
          <summary class="sub">Show the ${d.models.length} enabled models</summary>
          <ul>${d.models.map((m) => html`<li><code>${m}</code></li>`)}</ul>
        </details>` : null}

      <p class="sub">
        The guard repairs the collapse signature; it does not patch pi or PI WEB. If the file is
        rewritten again, the repair is logged here with a backup of what was there before.
      </p>
    </div>`;
}

function fetchInto(context) {
  if (CACHE.fetching) return;
  if (!context.peer || !context.peer.request) {
    CACHE.error = "No backend on this machine yet — restart the session daemon, then reload this page. " +
      "Your data is safe; the tab shows again after the restart.";
    return;
  }
  CACHE.fetching = true;
  context.peer.request("models", null)
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
