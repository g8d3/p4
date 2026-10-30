// p4.catalog — what plugins we built, why each one exists, and where to switch it on.
//
// Read-only on purpose: enable/disable is owned by the host (Settings → PI WEB plugins)
// and duplicating it here would drift. What the host cannot tell you is the reason.
import { CATALOG } from "./catalog-data.js";

const STYLE = `
.p4c { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; gap: 10px; padding: 12px; overflow: auto; }
.p4c h2 { margin: 0; font-size: 1rem; }
.p4c .sub { margin: 0; color: var(--pi-muted); font-size: .88rem; }
.p4c table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.p4c th { text-align: left; position: sticky; top: 0; background: var(--pi-surface, transparent); padding: 8px; font-size: .72rem;
          text-transform: uppercase; letter-spacing: .04em; color: var(--pi-muted); border-bottom: 1px solid var(--pi-border-muted); }
.p4c td { padding: 9px 8px; border-bottom: 1px solid var(--pi-border-muted); vertical-align: top; }
.p4c .name { font-weight: 600; white-space: nowrap; }
.p4c .id { font-family: ui-monospace, monospace; font-size: .76rem; color: var(--pi-muted); }
.p4c .why { color: var(--pi-muted); font-size: .92em; margin-top: 3px; }
.p4c .tag { display: inline-block; padding: 1px 7px; border-radius: 99px; font-size: .72rem; white-space: nowrap;
            border: 1px solid var(--pi-border-muted); color: var(--pi-muted); }
.p4c .t-shipped { color: var(--pi-success, #8ee6a8); }
.p4c .t-designed { color: var(--pi-warning, #c9a6ff); }
.p4c .t-patch { color: var(--pi-warning, #ffd479); }
.p4c .foot { color: var(--pi-muted); font-size: .82rem; }
.p4c .mine { color: var(--pi-muted); font-size: .82rem; }
`;

const tone = (status) =>
  status.startsWith("shipped") ? "t-shipped"
    : status.startsWith("designed") ? "t-designed"
      : status.startsWith("patch") || status.startsWith("upstream") ? "t-patch" : "";

function row(html, p) {
  return html`
    <tr>
      <td>
        <div class="name">${p.name}</div>
        <div class="id">${p.id}${p.source ? html`<span class="src"> · ${p.source}</span>` : null}</div>
      </td>
      <td>
        <div>${p.what}</div>
        <div class="why">Why: ${p.why}</div>
      </td>
      <td>${p.where}</td>
      <td>${p.kind}</td>
      <td><span class="tag ${tone(p.status)}">${p.status}</span></td>
    </tr>`;
}

function panel(html) {
  const mine = CATALOG.filter((p) => p.status.startsWith("shipped")).length;
  return html`
    <style>${STYLE}</style>
    <div class="p4c">
      <section>
        <h2>Plugins we built</h2>
        <p class="sub">
          ${mine} running, ${CATALOG.length} listed. Switch any of them on or off in
          <strong>Settings → PI WEB plugins</strong>; a plugin with a server entry needs the
          session daemon restarted before it takes effect.
        </p>
      </section>
      <table>
        <thead>
          <tr><th>Plugin (id · folder)</th><th>What and why</th><th>Where you see it</th><th>Kind</th><th>Status</th></tr>
        </thead>
        <tbody>${CATALOG.map((p) => row(html, p))}</tbody>
      </table>
      <p class="foot">
        A fix for PI WEB belongs here as a plugin, not as an edit to the core: a core edit is lost on the
        next update, a plugin is not. A plugin that is not in this table is not shipped.
      </p>
    </div>`;
}

const plugin = {
  apiVersion: 4,
  name: "Our PI WEB plugins",
  activate: ({ html, svg }) => ({
    contributions: {
      applicationPanels: [
        {
          id: "p4.catalog.panel",
          title: "Plugins",
          order: 980,
          icon: svg`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1"></rect>
            <rect x="14" y="3" width="7" height="7" rx="1"></rect>
            <rect x="3" y="14" width="7" height="7" rx="1"></rect>
            <rect x="14" y="14" width="7" height="7" rx="1"></rect>
          </svg>`,
          render: () => panel(html),
        },
      ],
    },
  }),
};

export default plugin;
