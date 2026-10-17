// Secrets box — PI WEB workspace panel.
//
// A password-type field whose content goes straight to this package's server peer
// (see src/server.mjs) and from there to the encrypted vault. It is never inserted
// into a message, so it cannot land in the session transcript.
//
// Deliberate properties (each one is asserted in test/panel.test.mjs):
//   - type="password" + autocomplete="new-password" + spellcheck="false"
//   - no console logging of any field value anywhere in this file
//   - fields are cleared from the DOM after a successful store, so the value does
//     not sit in the page for the next screenshot or devtools session
//   - only the secret NAME is ever rendered back to the user

const STYLE = `
.sb-form { display:grid; gap:.5rem; max-width:28rem; }
.sb-form label { display:flex; flex-direction:column; gap:.2rem; font-size:.85rem; opacity:.8; }
.sb-form input { padding:.45rem .5rem; border:1px solid color-mix(in srgb, currentColor 25%, transparent);
  border-radius:.4rem; background:transparent; color:inherit; font:inherit; }
.sb-row { display:flex; gap:.5rem; align-items:center; }
.sb-status { font-size:.85rem; margin-top:.4rem; }
.sb-ok { color:#1a7f37; } .sb-err { color:#b42318; }
.sb-names { font-size:.85rem; margin-top:.6rem; opacity:.85; }
.sb-warn { font-size:.8rem; margin-top:.8rem; opacity:.7; max-width:34rem; }
`;

export function createPanel(html) {
  // Per-workspace UI state. Only names and status live here — never a value.
  const states = new Map();

  function stateFor(context) {
    const key = `${context.machine.id}/${context.workspace.id}`;
    let state = states.get(key);
    if (!state) {
      state = { status: "", ok: true, names: [], busy: false };
      states.set(key, state);
    }
    return state;
  }

  function setStatus(state, ok, text) {
    state.ok = ok;
    state.status = text;
  }

  async function store(context, state, fields, host) {
    if (state.busy) return;
    const name = fields.name.value.trim();
    const value = fields.value.value;
    const passphrase = fields.passphrase.value;
    // Clear the DOM before the await: the value must not sit in the page while
    // a network hash to the peer is in flight, and not after either.
    fields.value.value = "";
    fields.passphrase.value = "";
    state.busy = true;
    setStatus(state, true, "Storing…");
    host.requestRender();
    try {
      const res = await context.peer.request("store", { name, value, passphrase });
      if (res && res.ok) {
        setStatus(state, true, `stored '${res.name}' (encrypted ${res.backend ?? "vault"}) — value discarded from the page`);
      } else {
        setStatus(state, false, `not stored: ${(res && res.error) || "unknown error"}`);
      }
    } catch (err) {
      setStatus(state, false, `peer error: ${err && err.message ? err.message : err}`);
    } finally {
      state.busy = false;
      host.requestRender();
    }
  }

  async function refresh(context, state, fields, host) {
    const passphrase = fields.passphrase.value;
    setStatus(state, true, "Reading names…");
    host.requestRender();
    try {
      const res = await context.peer.request("list", { passphrase });
      if (res && res.ok) {
        state.names = res.names;
        setStatus(state, true, `${res.names.length} secret name(s) in the vault`);
      } else {
        setStatus(state, false, `cannot list: ${(res && res.error) || "unknown error"}`);
      }
    } catch (err) {
      setStatus(state, false, `peer error: ${err && err.message ? err.message : err}`);
    } finally {
      fields.passphrase.value = "";
      host.requestRender();
    }
  }

  return {
    contributions: {
      workspacePanels: [
        {
          id: "secrets",
          title: "Secrets",
          render(context) {
            const state = stateFor(context);
            // Fields are DOM-owned, so render() cannot re-create them with stale
            // values: we keep the nodes once per panel host.
            let fields = context.host.__sbFields;
            if (!fields) {
              fields = {
                name: document.createElement("input"),
                value: document.createElement("input"),
                passphrase: document.createElement("input"),
              };
              fields.name.type = "text";
              fields.name.placeholder = "OPENAI_API_KEY";
              fields.name.autocomplete = "off";
              fields.name.spellcheck = false;
              fields.value.type = "password";
              fields.value.placeholder = "the secret value";
              fields.value.autocomplete = "new-password";
              fields.value.spellcheck = false;
              fields.passphrase.type = "password";
              fields.passphrase.placeholder = "vault passphrase";
              fields.passphrase.autocomplete = "new-password";
              fields.passphrase.spellcheck = false;
              context.host.__sbFields = fields;
            }
            const onStore = () => void store(context, state, fields, context.host);
            const onList = () => void refresh(context, state, fields, context.host);
            return html`
              <style>${STYLE}</style>
              <div class="sb-form">
                <label>Secret name<input .value=${fields.name.value} @input=${(e) => (fields.name.value = e.target.value)}></label>
                <label>Secret value (goes to the vault, not to the chat)</label>
                <div class="sb-row"><button id="sb-store" ?disabled=${state.busy} @click=${onStore}>Store as NAME</button></div>
                <label>Vault passphrase<input .value=${fields.passphrase.value} @input=${(e) => (fields.passphrase.value = e.target.value)}></label>
                <div class="sb-row"><button id="sb-list" ?disabled=${state.busy} @click=${onList}>Refresh names</button></div>
                <div class="sb-names">${state.names.length ? html`<div>${state.names.join(", ")}</div>` : ""}</div>
                <div class="sb-status ${state.ok ? "sb-ok" : "sb-err"}">${state.status}</div>
                <div class="sb-warn">The value is sent to the local vault: never to a chat message, a log, argv or a temp file. Values are only ever displayed masked (names only). If a real secret has ever been pasted into this chat, treat it as compromised and rotate it at the issuer.</div>
              </div>
            `;
          },
        },
      ],
    },
  };
}

const plugin = {
  apiVersion: 4,
  name: "Secrets box",
  activate({ html }) {
    return createPanel(html);
  },
};

export default plugin;
