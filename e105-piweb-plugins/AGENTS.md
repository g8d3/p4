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
docs/agent-cycles.md       design of the agent-cycles plugin
docs/current-models.md    your 4 picked models (the record; the guard enforces it)
models/models.js           p4.models guard: puts back missing picks from wanted.json (never removes, never rewrites picks)
models/server-plugin.js    server entry: runs the guard in the daemon, answers the Models panel
scripts/models.py          show | want | sync | check — the only writer of wanted.json; sync trims settings to picks
scripts/cycles.py          the ledger: what each session-daemon restart interrupted (CLI today)
                           systemd: p4-agent-cycles.service + .timer (every 15 min, boot)
                           output: <workspace>/.pi-web/agent_cycles.json
```

## Agent cycles: what exists

`scripts/cycles.py` derives, from evidence that already exists (systemd restarts + the session
transcripts under `~/.pi/agent/sessions`), which sessions were active in the 45 minutes before each
session-daemon restart and which never wrote again. On 2026-10-30 it found **21 interrupted agents
in 7 days** across 12 restarts.

```bash
cd /home/vuos/code/p4 && python3 e105-piweb-plugins/scripts/cycles.py --table   # see it
```
It runs every 15 minutes from `p4-agent-cycles.timer` and writes `<workspace>/.pi-web/agent_cycles.json`.

**How to test it yourself (one command):**

```bash
cd /home/vuos/code/p4 && python3 e105-piweb-plugins/scripts/selftest.py
```
It prints PASS/FAIL with the evidence for each check, and then lists what it does **not** cover —
the things that need a daemon restart or that would send a prompt to a live agent.

**Hot reload without daemon restarts (2026-10-30).** A plugin entry with a server entry pins its browser asset to the session daemon's *active* revision, so after any package update the tab 404s until the daemon restarts — the restart that orphans agents. Split pattern, now used by Cycles and Models: the feature id (`p4.cycles`, `p4.models`) is server-only (backend), and a second browser-only entry (`p4.cycles.panel`, `p4.models.panel`, no serverModule) holds the tab. Browser-only assets are served fresh on every page reload; the panel calls its backend over plain HTTP (`paired.js`: active revision from `/api/plugins` → `POST /api/paired-plugin-backends/<id>/...`). New panel code stays compatible with the old running backend (unknown input ignored there; sliced/defaulted here). Panel updates need only a browser reload now; backend updates still wait for the next natural daemon restart. Resuming the interrupted agents stays a Pi extension (see the design doc): this package reports, it does not resurrect.

Adding a plugin means adding an entry to `package.json`, a row to `catalog-data.js`, and a
note in `docs/`. A plugin that is not described in the catalog is not shipped.

## Conventions

- Name our plugin ids `p4.<something>`: in a list of fifteen they sort together and are the
  ones we can point at. This is why the catalog shows the id next to the name.
- The catalog is the index: a plugin that is not in `catalog/catalog-data.js` is not shipped,
  and the panel is the answer to "which of these are ours".
- `render` must return a template result from the host's `html` tag (`html\`...\``), not a DOM
  node. Returning an element fails activation silently: the tab simply never appears.
  Verify with a real browser, never by reading the code:

```bash
python3 - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page()
    pg.goto("http://127.0.0.1:8504/", wait_until="load"); pg.wait_for_timeout(5000)
    print([t for t in pg.eval_on_selector_all("button","e=>e.map(x=>x.textContent.trim())") if "Plugins" in t])
    b.close()
PY
```
