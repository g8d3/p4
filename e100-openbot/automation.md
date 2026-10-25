# e100-openbot — GUI automation: screenshots vs accessibility tree vs CDP

## Verdict
CDP wins. It reads the whole app as ~1KB of text in ~80ms and clicks by name.
Screenshots are the fallback of last resort. The accessibility tree sits in the
middle: useful, but needs extra setup on Linux.

## Numbers from this session (Oct 24, 2026)

| Method | Ops | Cost per state read | Failures hit |
|---|---|---|---|
| Screenshots + xdotool coords | 27 screenshots (2.5MB), ~15 image reads, ~20 xdotool ops | 1 screenshot + 1 vision read (~35–110KB image); coordinate guessing | 4+ mis-clicks (Settings→Marketplace x2, missed clear-search x, hit "+" instead of row, model-server list clone bug); ~6 min from first screenshot to the key dialog |
| ATSPI tree (pyatspi) | 3 scripts | full-tree search 0.0s once running | 3 setup blockers: wrong API (`Registry()` not `getRegistry()`); empty tree until relaunch with `--force-renderer-accessibility`; no a11y bus until `at-spi-bus-launcher --launch-immediately` |
| CDP (`obctl.py`) | ~20 scripts, 0 images | 5 text reads in 0.41s (~80ms each, ~1KB) | 2 setup blockers: needs `--remote-allow-origins=*`; arrow-fn expressions must be invoked (IIFE) |

Real cost of screenshots is not capture (60ms) — it is the vision read plus
another round trip for every guess, with no element identity. CDP keeps element
identity (ids like `dropdownmenu-cl-13-trigger`, `cl-128-control`), so retries
are free.

## Working recipe (all three, cheapest first)

1. Launch once with everything on:
   ```
   Xvfb :99 &
   dbus-launch --sh-syntax > /tmp/obenv && source /tmp/obenv
   echo -n "" | gnome-keyring-daemon --daemonize --components=secrets --login
   at-spi-bus-launcher --launch-immediately &
   OpenBot-x86_64.AppImage --no-sandbox --force-renderer-accessibility \
     --remote-debugging-port=9222 --remote-allow-origins=*
   ```
2. Drive with CDP: `python3 obctl.py text|eval|click` (no screenshots).
3. Use ATSPI only for what CDP cannot see (native file dialogs, tray).
   Needs `DISPLAY` + DBUS session exported, same machine.
4. Screenshots only to visually confirm a final state for a human.

## Quirks found
- Synthetic mouse events open Radix menus, but menu items only activate with
  keyboard Enter on the focused `[role=menuitem]`, not with click events.
- After relaunch, OpenBot signs out (account session lived in secure storage,
  which was unavailable) — budget one email-code round per relaunch.
- OpenCode Go key save fails with "System secret storage is unavailable"
  unless the app sees a working D-Bus secret service at launch (still open).
