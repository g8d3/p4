// p4.catalog — a read-only list of the PI WEB plugins we built and why.
//
// Deliberately read-only: enabling and disabling is owned by the host
// (Settings → PI WEB plugins) and this panel points there instead of
// duplicating it. What the host cannot tell you is why each plugin exists.
import { CATALOG } from "./catalog-data.js";

const STYLE = `
.wrap{font:13px/1.5 system-ui,sans-serif;color:var(--pi-text,#e6e9f0);padding:14px 16px;max-width:900px}
h2{font-size:1rem;margin:0 0 2px}
.sub{color:var(--pi-muted,#8b93a7);margin:0 0 14px}
table{width:100%;border-collapse:collapse}
th{text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--pi-muted,#8b93a7);
   font-weight:600;padding:8px 8px;border-bottom:1px solid var(--pi-border,#232a3a);position:sticky;top:0}
td{padding:9px 8px;border-bottom:1px solid var(--pi-border-soft,#161c2b);vertical-align:top}
tr:hover td{background:var(--pi-hover,#111624)}
.name{font-weight:600;white-space:nowrap}
.id{font-family:ui-monospace,monospace;font-size:.78rem;color:var(--pi-muted,#8b93a7)}
.what{color:var(--pi-text,#e6e9f0)}
.why{color:var(--pi-muted,#8b93a7);font-size:.9em;margin-top:3px}
.tag{display:inline-block;padding:1px 7px;border-radius:99px;font-size:.72rem;border:1px solid var(--pi-border,#2b3550);
     color:var(--pi-muted,#9fb0cc);white-space:nowrap}
.shipped{color:#8ee6a8;border-color:#2b5c3f}.designed{color:#c9a6ff;border-color:#43305c}
.patch{color:#ffd479;border-color:#5c4a20}.convention{color:#7cc4ff;border-color:#274a6b}
.foot{margin-top:14px;color:var(--pi-muted,#8b93a7);font-size:.85rem}
`;

function render(html, context) {
  const rows = CATALOG.map((p) => {
    const tone = p.status.startsWith("shipped") ? "shipped" : p.status.startsWith("designed") ? "designed"
      : p.status.startsWith("patch") || p.status.startsWith("upstream") ? "patch" : "convention";
    return `<tr>
      <td><div class="name">${html.escape(p.name)}</div><div class="id">${html.escape(p.id)}</div></td>
      <td><div class="what">${html.escape(p.what)}</div><div class="why">Why: ${html.escape(p.why)}</div></td>
      <td>${html.escape(p.where)}</td>
      <td>${html.escape(p.kind)}</td>
      <td><span class="tag ${tone}">${html.escape(p.status)}</span></td>
    </tr>`;
  }).join("");
  const root = html.el("div", { class: "wrap" });
  root.innerHTML = `<h2>Plugins we built</h2>
    <p class="sub">What each one does and why it exists. Turn one on or off in <b>Settings → PI WEB plugins</b>;
    a server-backed change needs the session daemon restarted.</p>
    <table><thead><tr><th>Plugin</th><th>What and why</th><th>Where you see it</th><th>Kind</th><th>Status</th></tr></thead>
    <tbody>${rows}</tbody></table>
    <p class="foot">Fixes for PI WEB belong here as plugins, not as edits to the core: a core edit is lost on the
    next update, a plugin is not.</p>`;
  return root;
}

const plugin = {
  apiVersion: 4,
  name: "Our PI WEB plugins",
  activate: ({ html, svg }) => {
    const style = html.el("style");
    style.textContent = STYLE;
    return {
      contributions: {
        applicationPanels: [
          {
            id: "p4.catalog.panel",
            title: "Plugins",
            order: 980,
            icon: svg`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"></rect>
              <rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect>
              <rect x="14" y="14" width="7" height="7" rx="1"></rect></svg>`,
            render: (context) => {
              const box = render(html, context);
              box.prepend(style.cloneNode(true));
              return box;
            },
          },
        ],
      },
    };
  },
};

export default plugin;
