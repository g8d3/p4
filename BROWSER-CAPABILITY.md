# Browser Capability Inventory — proven on THIS box (2026-09-29)

Machine: Linux x86_64. All commands below were executed here and their
outputs verified, not asserted.

## Binaries

| Tool | Path / version | Status |
|---|---|---|
| `agent-browser` | `/home/vuos/.nvm/versions/node/v24.16.0/bin/agent-browser` | WORKS — drove both apps, screenshots saved |
| `google-chrome` | `/usr/local/bin/google-chrome`, `153.0.8010.47` | WORKS — engine behind agent-browser |
| `Xvfb` / `xvfb-run` | `/usr/bin/Xvfb`, `/usr/bin/xvfb-run` | PRESENT (headed mode possible, not yet tested) |
| e020 benchmark scripts | `e020-undetectable-browser-benchmark/ag-01/bin/` (9 scripts) | Present, results on disk (see below) |

## Exact working command patterns (agent-browser)

```bash
# Isolated session per task (state persists across calls in the session)
agent-browser --session-name <name> open http://127.0.0.1:8342/
agent-browser --session-name <name> snapshot -i        # interactive refs @eN
agent-browser --session-name <name> click @e6          # refs go stale after nav — re-snapshot
agent-browser --session-name <name> fill @e4 "text"
agent-browser --session-name <name> press Enter
agent-browser --session-name <name> scroll down 600    # humanized scroll
agent-browser --session-name <name> wait 1500          # humanized delay (ms)
agent-browser --session-name <name> set viewport 1366 900   # NOT `viewport 1366x900`
agent-browser --session-name <name> eval "document.title"   # JS eval, JSON out
agent-browser --session-name <name> screenshot body /abs/path.png  # ONE arg = selector; path MUST be 2nd arg + absolute
agent-browser --session-name <name> open <url> --headed     # headed flag exists (needs display/Xvfb)
```

Gotchas found by doing:
- `viewport 1366x900` → `Unknown command: viewport`. Correct: `set viewport 1366 900`.
- `screenshot ./rel/path.png` (single arg) is treated as a CSS **selector** and the
  file lands in `~/.agent-browser/tmp/screenshots/`. Correct: `screenshot body /abs/path.png`.
- No `status`/`tabs` commands. Refs (`@eN`) are re-assigned every snapshot.

## Humanized-behavior proof (this session)

Drove e082 (`:8342`) and e083 (`:8383`): open → snapshot → `set viewport 1366 900` →
scroll down/up with `wait` delays → full eval reads → screenshots.
Screenshots: `.growth-shots/e082-hero.png`, `.growth-shots/e083-hero.png`,
`.growth-shots/bot-sannysoft.png`.

Eval fingerprint on this box:
`ua=Chrome/149 … webdriver=true, chrome=true, plugins=5, tz=America/Bogota, mem=8, touch=0`.

## Detection score (measured, bot.sannysoft.com 2026-09-29)

| Test | Result |
|---|---|
| User-Agent | passes (real Chrome string) |
| **WebDriver (New)** | **present (FAILED) — `navigator.webdriver=true`, headless tell** |
| WebDriver Advanced | passed |
| Chrome object | present (passed) |
| Permissions / Plugins / Languages / WebGL vendor | passed |
| Phantom / Headless-Chrome fingerprint suite | all `ok` |
| WebGL renderer | `ANGLE … SwiftShader` = software rendering (headless tell) |

Net: agent-browser headless is **honest automation, not undetectable**.
It sails through casual checks and everything Google-search-level (see e020),
but a strict detector (`navigator.webdriver`, SwiftShader) flags it.

## Headless vs headed (this box — headed TESTED 2026-09-29)

| Mode | Status |
|---|---|
| Headless (default) | PROVEN — all of the above |
| Headed (`open --headed` under Xvfb `:99`) | PROVEN — re-scored sannysoft, see table below |

### Headed upgrade — exact working recipe (L4 spike 2026-09-29)

Pre-existing `Xvfb :99` was already live on this box (PID 974655, since
Sep 26); a second `Xvfb :99 -screen 0 1366x900x24` was NOT needed. The
agent-browser daemon holds ONE mode at a time — `--headed` on `open` is
silently ignored while a headless daemon runs, so `close` first:

```bash
agent-browser close
DISPLAY=:99 agent-browser --session-name <name> open <url> --headed
# EVERY later call in the session needs the same prefix:
DISPLAY=:99 agent-browser --session-name <name> eval "..."
DISPLAY=:99 agent-browser --session-name <name> screenshot body /abs/path.png
agent-browser close   # return the daemon to clean state when done
```

Gotchas found by doing:
- `open <url> --headed` while daemon alive →
  `⚠ --headed ignored: daemon already running. Use 'agent-browser close'
  first`. The open still succeeds — but HEADLESS. Always `close` first.
- `DISPLAY` is empty in a fresh shell; without the prefix the headed
  browser cannot start. `:99` (not a fresh `xvfb-run -a`) is the pinned
display on this box.

### Headed vs headless detection (bot.sannysoft.com, same day, same box)

| Test | Headless | Headed (Xvfb :99) |
|---|---|---|
| WebDriver (New) | present (**FAILED**) | present (**STILL FAILED**) — CDP drives it either way |
| WebDriver Advanced | passed | passed |
| Chrome object | present (passed) | present (passed) |
| WebGL renderer | `ANGLE … SwiftShader` = software rendering (headless tell) | `ANGLE (Mesa, llvmpipe LLVM 20.1.2, OpenGL 4.5)` — real Mesa stack, SwiftShader tell GONE |
| WebGL vendor | passed | `Google Inc. (Mesa)` |
| Window chrome | headless (no outer chrome) | `wOuterHeight 1004 > wInnerHeight 914, wOuterWidth 1050` — real window frame |
| Permissions (New) | passed | `prompt` |
| Phantom / Headless-Chrome suite | all `ok` | all `ok` |

Screenshot: `.growth-shots/sanny-headed-xvfb.png`.

Net: headed-under-Xvfb removes the GPU + window-chrome tells but does
NOT kill `navigator.webdriver` — agent-browser drives via CDP, and CDP
sets the flag in both modes. True undetectability needs the e020 path
(Camoufox / undetected-chromedriver with NON-CDP driving), not flags on
this tool. L4 stays OPEN; next slice is a Camoufox-vs-CDP comparison.

## Driven-browser telemetry convention (MANDATORY, 2026-09-29)

All future driven-browser passes MUST self-identify so agent traffic never
pollutes the human funnel: open every URL as `<url>?agent=<reason>` (e.g.
`http://127.0.0.1:8342/?agent=ux-seat-pass`). The page snippet saves the name
to `localStorage` and forwards it as `agent:<name>` on every telemetry event;
the server tags those events `synthetic:true` (name preserved, hidden from
human counts by default, revealed under `?bots=1`). Browsers WITHOUT the flag
still count as human — so an untagged pass is a human-attributed visit. Keep
`<reason>` to `[A-Za-z0-9_.-]`, max 64 chars.

```bash
agent-browser --session-name <name> open http://127.0.0.1:8342/?agent=<reason>
```

## e020 benchmark results (prior art, on disk)

`e020-undetectable-browser-benchmark/ag-01/output/`: 6/7 setups pass Google
captcha+search headless with fresh profiles (Camoufox, Chrome, Firefox,
undetected-chromedriver, Playwright+stealth). Puppeteer Extra + stealth passed
captcha but **failed search**. Only the real Chrome profile is authenticated;
per e020's warning, never copy its cookies elsewhere (session-theft flag risk).

## What agents CAN / CANNOT do with browsers here (owner limits respected)

- CAN: drive pages with humanized delays/scroll/viewport, screenshot, fill forms
  in logged-in sessions, read any public state.
- CANNOT (by undetectability): pass strict bot walls headless — WebDriver flag is set.
  Upgrade path: Xvfb headed + stealth patches (unproven here), or Camoufox per e020.
- NEVER: create accounts, publish/post/send, spend money — all growth-task
  outputs are prepared copy, gated `[NEEDS OWNER TAP]`.
