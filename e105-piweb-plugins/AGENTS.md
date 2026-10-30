# e105 — PI WEB plugins we build

One package, several plugins. Each fix or addition for PI WEB lands here as a plugin
instead of an edit to the core: a core edit is lost on the next update, a plugin is not.

## Product

| Surface | User action |
|---|---|
| PI WEB tab **Plugins** (this package, `p4.catalog`) | Read what every plugin we built does, why it exists, where you see it, what kind it is, and whether it runs yet. Turn one on or off in Settings → PI WEB plugins (this panel deliberately does not duplicate that). |

## Install (no rebuild of PI WEB)

```bash
ln -s /home/vuos/code/p4/e105-piweb-plugins ~/.pi-web/plugins/p4-plugins
```
Browser-only plugin: reload the browser page. A plugin with a **server entry** needs the
session daemon restarted (it interrupts working agents — do it when nothing is running),
then reload.

Verify what the host actually sees:

```bash
curl -s localhost:8504/api/plugins | python3 -c "import json,sys;print([p['id'] for p in json.load(sys.stdin)['plugins']])"
```

## Contents

```
package.json          piWeb.plugins: the entries this package ships
catalog/pi-web-plugin.js   p4.catalog — read-only catalog panel
catalog/catalog-data.js    the catalog itself (id, what, why, where, kind, status)
docs/agent-cycles.md       design of the agent-cycles plugin (designed, not built)
```

Adding a plugin means adding an entry to `package.json`, a row to `catalog-data.js`, and a
note in `docs/`. A plugin that is not described in the catalog is not shipped.
