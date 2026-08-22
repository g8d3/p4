# Fleet identification: arnes, modelo, proveedor

How to answer "what is running in tmux window N?" — learned the hard way in this
session. No single command is enough; you need two independent sources.

## Vocabulary (do not mix these)

- **Arnés (harness)** — the TUI/binary the agent talks through: `opencode`,
  `command-code`, `fx`, etc.
- **Modelo** — the LLM identity answering: `Ox Alpha`, `Muse Spark 1.2 Contributor`.
- **Proveedor** — the API route serving it: `OpenRouter`, `OpenCode Go`, `Command Code`.

Example decomposition of a status-bar line `Build · Ox Alpha OpenRouter`:
harness=opencode, model=Ox Alpha, provider=OpenRouter. The same model can arrive
through different providers, and the same harness can serve different models.

## The three commands

### 1. Binary level — what process owns the pane

```bash
tmux list-panes -a -F "#{session_name}:#{window_index} win=#{window_name} \
cmd=#{pane_current_command} title=#{pane_title} pid=#{pane_pid} tty=#{pane_tty}"

# real child of the pane's shell:
ps --ppid <pane_pid> -o pid,args
# or everything on that tty:
ps -t <tty-without-/dev/> -o pid,args
```

- `opencode2` reports itself honestly (`cmd=opencode2`).
- Command Code does **not**: it sets `process.title = "⌘ Introduction"`, which
  overwrites `/proc/pid/cmdline`, `ps args`, and `comm`. You will see a node
  process whose argv is literally `⌘ Introduction`. So binary level alone cannot
  distinguish Command Code from any other node TUI.

### 2. UI level — branding lives only on screen

```bash
tmux capture-pane -p -S -800 -t <index>
```

What to look for:

| Harness | Where | What it shows |
|---|---|---|
| opencode | bottom status bar | `Build · <model> <provider>` (e.g. `Build · Muse Spark 1.2 Contributor OpenCode Go`) |
| command-code | top header | `Command Code v1.32.1   models: muse-spark-1.2-contributor · taste-1` |

Caveats:

- The footer scrolls away; use `-S -800` (or more) to reach it.
- A busy agent repaints its pane constantly; capture may catch mid-frame output.
- opencode footer may say `OpenCode Zen` while env points at the Go endpoint
  (`OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1/`) — treat Zen-branded Go
  routes as provider `OpenCode Go`.

### 3. Cross-check both

Decision table:

| `list-panes`/`ps` says | `capture-pane` says | Conclusion |
|---|---|---|
| `opencode2` | `Build · X Y` | harness=opencode, model=X, provider=Y |
| `node` + `⌘ Introduction` | `Command Code vX.Y.Z ...` | harness=command-code |
| `node` + `⌘ Introduction` | no CC header, opencode-like bar | inspect more history (`-S -3000`) |

Never conclude from one source alone:

- Footer alone lies when history was overwritten (a0 was misread as opencode-go
  because an old `OpenCode Go` footer survived in scrollback).
- `ps` alone lies because of `process.title` overwrites.

## Optional deep checks (rarely needed)

```bash
tr '\0' '\n' < /proc/<pid>/environ | grep -E "OPENCODE_GO|OPENROUTER|MODEL"
readlink /proc/<pid>/exe     # confirms node vs native binary
readlink /proc/<pid>/cwd     # working dir of the agent
```

Env vars shared by all panes (same shell profile) prove available providers but
NOT which one a given window uses — selection is runtime state inside each TUI.

## Renaming convention

```bash
for i in $(seq 0 $(($(tmux list-windows -t main | wc -l) - 1))); do
  tmux rename-window -t main:$i "a$i"
done
```

Regrouping windows (e.g. all OpenCode left, all Command Code right):

```bash
tmux swap-window -s main:0 -t main:2   # swap contents of two indices
```
