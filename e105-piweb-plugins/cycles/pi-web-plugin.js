// p4.cycles — what the restarts did to the agents, in the selected workspace.
//
// Layout decision: this is a LOG, not a comparison matrix, so it is rendered as cards, not a table.
// That is also the answer to the mobile problem — a table with five columns made the row as tall as
// the longest list and squeezed the only text that matters into a sliver on a phone. A card keeps
// one restart together at any width, and the lost-agent list collapses instead of stretching it.
//
// Times: rendered with toLocaleString in the VIEWER's zone. A sliced ISO string shows UTC as if it
// were local (a 23:41 restart read as 04:41), and a hardcoded zone is wrong for everyone else.
//
// Read-only: resuming is a dispatch and belongs to piweb-restart, not to a panel.
const CACHE = new Map();
const REFRESH_MS = 20000;

const STYLE = `
.p4c{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;gap:14px;padding:14px;overflow:auto}
.p4c h2{margin:0;font-size:1rem}
.p4c h3{margin:0 0 6px;font-size:.82rem;text-transform:uppercase;letter-spacing:.05em;color:var(--pi-muted)}
.p4c .sub{margin:0;color:var(--pi-muted);font-size:.85rem;line-height:1.45}
.p4c .cards{display:grid;gap:10px}
.p4c .card{border:1px solid var(--pi-border-muted);border-radius:10px;padding:10px 12px;
  display:flex;flex-direction:column;gap:8px;min-width:0}
.p4c .card.bad{border-color:var(--pi-warning,#ffd479)}
.p4c .head{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;justify-content:space-between}
.p4c .when{font-variant-numeric:tabular-nums;font-weight:600;font-size:.9rem}
.p4c .chips{display:flex;flex-wrap:wrap;gap:6px}
.p4c .chip{font-size:.75rem;padding:1px 8px;border-radius:99px;border:1px solid var(--pi-border-muted);
  color:var(--pi-muted);white-space:nowrap}
.p4c .chip.ok{color:var(--pi-success,#8ee6a8)}
.p4c .chip.bad{color:var(--pi-warning,#ffd479);font-weight:600}
.p4c .row{display:flex;gap:6px;align-items:baseline;font-size:.84rem;min-width:0}
.p4c .k{color:var(--pi-muted);flex:0 0 auto}
.p4c .v{min-width:0;overflow-wrap:anywhere}
.p4c details{margin:0}
.p4c summary{cursor:pointer;color:var(--pi-muted);font-size:.84rem}
.p4c ul{margin:6px 0 0 16px;padding:0;font-size:.82rem;color:var(--pi-muted)}
.p4c li{overflow-wrap:anywhere}
.p4c .empty{color:var(--pi-muted);font-size:.86rem;line-height:1.5}
.p4c code{font-family:ui-monospace,monospace;font-size:.85em}
@media (min-width:760px){ .p4c .cards{grid-template-columns:repeat(auto-fill,minmax(340px,1fr))} }
`;

const time = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return String(iso);
  return d.toLocaleString(undefined, {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  });
};
const clock = (ms) => {
  if (ms === null || ms === undefined) return "—";
  const n = Number(ms);
  if (!isFinite(n)) return "—";
  return n < 1000 ? `${n} ms` : `${(n / 1000).toFixed(1)} s`;
};

function chips(html, items) {
  return html`<div class="chips">${items.map(([label, tone]) =>
    html`<span class="chip ${tone || ""}">${label}</span>`)}</div>`;
}

// One restart as reported by cycles.py: who was working, who came back, who never wrote again.
function cycleCard(html, c) {
  const lost = c.interrupted || [];
  const working = (c.working || []).length;
  const resumed = (c.resumed || []).length;
  return html`
    <div class="card ${lost.length ? "bad" : ""}">
      <div class="head">
        <span class="when">${time(c.boot)}</span>
        ${chips(html, [[`${working} working`, ""], [`${resumed} resumed`, resumed ? "ok" : ""],
                       [`${lost.length} lost`, lost.length ? "bad" : "ok"]])}
      </div>
      ${lost.length ? html`
        <details>
          <summary>Show the ${lost.length} that never wrote again</summary>
          <ul>${lost.map((w) => html`<li>${(w.title || w.id || "").slice(0, 90)}
            <span class="k"> · last write ${time(w.last)}</span></li>`)}</ul>
        </details>` : html`<div class="row"><span class="v">Nothing was lost in this restart.</span></div>`}
    </div>`;
}

// One audited run by piweb-restart: what it decided, how long each phase took, what it resumed,
// and whether that resume was confirmed by the session writing afterwards.
function auditCard(html, r) {
  const lost = r.lost || [];
  const resumed = r.resumed || [];
  const failed = r.failed || [];
  const verified = r.verified || [];
  const phases = r.phases_ms || {};
  const bad = r.result !== "ok";
  return html`
    <div class="card ${bad ? "bad" : ""}">
      <div class="head">
        <span class="when">${time(r.started)}</span>
        ${chips(html, [[r.mode || "wait", ""], [`${r.result || "?"}`, bad ? "bad" : "ok"],
                       [`${clock(r.total_ms)}`, ""]])}
      </div>
      <div class="row"><span class="k">stopped</span><span class="v">${(r.stopped || []).length} session(s),
        ${(r.cut || []).length} turn(s) cut</span></div>
      <div class="row"><span class="k">resumed</span><span class="v">${resumed.length} accepted ·
        ${verified.length} confirmed writing · ${failed.length} rejected · ${lost.length} lost</span></div>
      <div class="row"><span class="k">phases</span><span class="v">
        ${Object.entries(phases).filter(([, v]) => v).map(([k, v]) => `${k} ${clock(v)}`).join(" · ") || "—"}
      </span></div>
      ${(r.restart && r.restart.confirmed) ? html`<div class="row"><span class="k">restart</span>
        <span class="v">${r.restart.confirmed}</span></div>` : null}
      ${lost.length || failed.length ? html`
        <details>
          <summary>Show what did not come back</summary>
          <ul>${lost.map((x) => html`<li>${(x.id || "").slice(0, 12)} — prompt accepted, never wrote again</li>`)}
              ${failed.map((x) => html`<li>${(x.id || "").slice(0, 12)} — ${x.detail || "rejected"}</li>`)}</ul>
        </details>` : null}
    </div>`;
}

function agentCard(html, a) {
  return html`
    <div class="card ${a.state === "busy" ? "" : ""}">
      <div class="head">
        <span class="when">${a.state === "busy" ? "busy" : a.state}</span>
        ${chips(html, [[a.last || "?", a.state === "busy" ? "bad" : "ok"]])}
      </div>
      <div class="row"><span class="k">session</span><span class="v">${(a.session || "").slice(0, 20)}</span></div>
      <div class="row"><span class="k">since</span><span class="v">${time(a.at)}</span></div>
      ${a.cwd ? html`<div class="row"><span class="k">folder</span><span class="v">${a.cwd}</span></div>` : null}
    </div>`;
}

function view(html, entry) {
  const d = entry.data || {};
  const cycles = (d.cycles || []).slice().reverse();
  const audit = (d.audit || []).slice().reverse();
  const agents = d.activity || [];
  const busy = agents.filter((a) => a.state === "busy").length;
  return html`
    <style>${STYLE}</style>
    <div class="p4c">
      <section>
        <h2>Agent cycles</h2>
        <p class="sub">
          ${busy ? html`<strong>${busy} agent(s) working right now.</strong> ` : null}
          ${d.generated_at ? html`Ledger built ${time(d.generated_at)} · ${cycles.length} restart(s) recorded.`
            : html`No ledger in this workspace yet.`}
          Times are shown in your own time zone.
        </p>
      </section>

      ${entry.error ? html`<p class="empty">${entry.error}</p>` : null}

      ${agents.length ? html`
        <section>
          <h3>Right now</h3>
          <div class="cards">${agents.slice(0, 12).map((a) => agentCard(html, a))}</div>
        </section>` : null}

      ${audit.length ? html`
        <section>
          <h3>Restart runs (audited)</h3>
          <div class="cards">${audit.slice(0, 10).map((r) => auditCard(html, r))}</div>
        </section>` : html`
        <section>
          <h3>Restart runs (audited)</h3>
          <p class="empty">No audited run yet. <code>piweb-restart</code> writes one line per run to
          <code>.pi-web/restart_audit.jsonl</code>.</p>
        </section>`}

      <section>
        <h3>Restarts that interrupted agents</h3>
        ${cycles.length ? html`<div class="cards">${cycles.slice(0, 12).map((c) => cycleCard(html, c))}</div>`
          : html`<p class="empty">None in this window — or the ledger has not been generated here yet.</p>`}
      </section>

      <p class="sub">
        Read-only. Resuming an interrupted agent is a dispatch, and that is <code>piweb-restart</code>'s job;
        this panel reports what happened, including the runs where the resume was accepted and the session
        never wrote again.
      </p>
    </div>`;
}

function keyOf(context) {
  const w = context.workspace || {};
  return `${(context.machine && context.machine.id) || ""}|${w.path || ""}`;
}

function fetchInto(context) {
  const key = keyOf(context);
  const entry = CACHE.get(key) || { data: null, fetching: false, error: null, at: 0 };
  CACHE.set(key, entry);
  if (entry.fetching) return entry;
  if (!context.peer || !context.peer.request) {
    entry.error = "This machine has no backend for the package: enable the plugin and restart the session daemon.";
    return entry;
  }
  entry.fetching = true;
  context.peer.request("state", null)
    .then((res) => {
      entry.data = res && typeof res === "object" ? res : null;
      entry.error = null;
      entry.at = Date.now();
    })
    .catch((err) => { entry.error = String((err && err.message) || err); })
    .finally(() => {
      entry.fetching = false;
      try { context.host.requestRender(); } catch { /* tab closed */ }
    });
  return entry;
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
            let entry = CACHE.get(keyOf(context));
            if (!entry || (!entry.data && !entry.fetching && !entry.error)
                || (entry.at && Date.now() - entry.at > REFRESH_MS)) {
              entry = fetchInto(context);
            }
            return view(html, entry);
          },
        },
      ],
    },
  }),
};

export default plugin;
