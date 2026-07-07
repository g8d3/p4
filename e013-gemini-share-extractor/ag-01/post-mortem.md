# Post‑mortem: extracting a Gemini share conversation

**Date**: 2026-07-06
**Experiment**: e013 — Gemini Share Extractor
**Agent**: ag-01

## The task

Extract the text of a conversation from a Gemini share URL
(`https://share.gemini.google/<id>`).

## What I tried (in order)

| Attempt | Time | Result | Why it (didn't) work |
|---|---|---|---|
| 1. `curl` the share URL | 1.1 s | HTML app shell only | The page is a JS SPA — the conversation is never in the static HTML. |
| 2. `curl` + grep for patterns | ― | Found only sample prompts from `WIZ_global_data`, not the actual share. | The share data is loaded via an authenticated API call, not embedded in the page. |
| 3. `google-chrome --headless --dump-dom` | **~30 s** | ✅ Full rendered DOM (1.7 MB) | `--dump-dom` forces Chrome to render, but it waits for the page's `load` event. Gemini's SPA spins background timers, API polling, and TF Lite init, delaying `load` by ~25 s. |
| 4. CDP `Page.navigate` + `Runtime.evaluate` | never | DOM = 4 elements (empty) | Headless Chrome without `--dump-dom` (or a rendering trigger like screenshot) **never commits** the JS-rendered DOM to the live document. JS runs, but the pipeline stops before layout/paint. |
| 5. CDP + forced `Page.captureScreenshot` | never | Same — empty DOM | Even screenshot doesn't populate `document.body`. The Gemini SPA may render into Shadow DOM or a detached tree. |
| 6. CDP + `--dump-dom` simultaneously | ~30 s | DOM empty during render, full only at the end | `--dump-dom` accumulates DOM internally and flushes at process exit. It is **not** accessible via CDP during execution. |
| **7. agent-browser `open` + `wait --load networkidle` + `get text body`** | **3.5 s** ✅ | Clean conversation text | agent-browser launches Chrome with the correct headless flags, and `get text` extracts rendered text properly (UI Automation / CDP's `getDocument`?). |

## Why did agent-browser work?

Two reasons:

### 1. Correct Chrome launch flags

agent-browser does **not** use `--dump-dom`. It launches Chrome in standard `--headless` mode
(Puppeteer-style), which **does** run the full rendering pipeline (style, layout, paint).
My manual CDP attempts used raw `Page.navigate` which skipped that pipeline.

### 2. The tool exists

agent-browser is already installed, documented in `e000-fundamentals/AGENTS.md`,
and battle-tested in this project. I jumped directly to **building from scratch**
(step 4 of the hierarchy below) without first checking **which tool already solves this**.

## The tool hierarchy (learned)

When facing a problem — **try in this order:**

1. **Existing script in the project** — `pdw`, `nova-chrome`, `record.sh`
2. **Existing CLI tool** — `agent-browser`, `ffmpeg`, `swaymsg`
3. **Build a new script** — short Python/bash using existing tools
4. **Build from scratch** — raw CDP, raw IPC, raw protocols

**I went 4 → 3 → 2**. The correct path is **2 → 3 → 4** (3 and 4 only when 2 doesn't exist).

## The architecture lesson

### `output/` follows the agent, not the experiment

Files an agent produces belong in its own directory:

```
e013/
├── ag-01/
│   ├── output/       ← owned by this agent
│   └── bin/          ← scripts owned by this agent
```

This replaces the previous convention of a shared `output/` at the experiment
level, which mixed outputs from different agents with no clear ownership.

### AGENTS.md should be short

The `e000-fundamentals/AGENTS.md` is 714 lines. An agent has to digest all of
it before acting. The solution (pointed out by the user) is to **extract
procedural logic into skills and scripts**, leaving AGENTS.md with **declarative
instructions only**.

## The measurement principle (violated)

I ran many commands without understanding what I was measuring:

| What I should have done | What I did |
|---|---|
| Measure Chrome startup + page load separately first | Jumped straight into CDP experiments |
| Stop after 2 failed approaches and think | Ran 6+ approaches before finding the right one |
| Ask "what tool already does this?" | Asked "how can I build this?" |

A simple rule: **if a command takes > 5 s, cancel it and think first**.

## The actual bottleneck

Not CPU. Not network. **Chrome `--dump-dom` waits for the SPA's `load` event.**
Gemini's SPA has:
- TensorFlow Lite (Wasm) initialization
- Background polling / API calls
- Long `setTimeout` chains

`--dump-dom` serializes the page when everything is "done". agent-browser extracts
text as soon as the conversation is visually rendered, without waiting for the
entire SPA to idle.

**Measured overhead of `--dump-dom`:**

| Phase | Time |
|---|---|
| Real page load (agent-browser) | ~3.5 s |
| Extra wait for SPA idle (`--dump-dom`) | ~26.5 s |
| **Waste** | **88 % of total time** |
