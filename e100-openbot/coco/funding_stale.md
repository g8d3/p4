# Funding-rates page stale since 2026-10-24 09:51 — cause and smallest fix

Read-only investigation, 2026-10-25 19:45 Bogotá. No services started, enabled, published or pushed.

## Cause (two independent things)

1. **The hourly publisher timer is stopped and disabled.**
   - `systemctl --user show echolike-funding-page.timer`: `UnitFileState=disabled`, `ActiveState=inactive`, `LastTriggerUSec` empty.
   - `journalctl --user -u echolike-funding-page.timer`: `Started` Oct 23 09:23:35, **`Stopped` Oct 23 23:36:14**, no run after that.
   - The timer was not failing; it was stopped. So `funding_publicar.sh` has not run since.
   - (Our shell's `DBUS_SESSION_BUS_ADDRESS` points at a stale `/tmp/dbus-*`; with `unix:path=/run/user/1000/bus` the unit state is readable. This is not the cause, just why a plain `systemctl --user` call errors.)

2. **The last actual publish attempt was blocked by a real gate failure, not a data/key error.**
   - `funding_publicar.log` last lines:
     - `2026-10-24 09:51:21 screener rc=0 33508ms`
     - `2026-10-24 09:51:22 page 42ms`, `test_funding_page OK`, `directory QA ok`
     - `2026-10-24 09:53:37 click-through FAIL, not published`
   - `reportes/recorrido_2026-10-24_funding.md`: **1 high, 0 critical/medium** — `/` `home_missing_section`: home does not link to `private/progress/`.
   - That link now exists in the current source and local build (`64a9ab6`, `unico/index.html` contains `private/progress/`), so the specific blocker is fixed.
   - The data is not missing or stale: `estado/funding_publico.json` is **2026-10-25T21:52:03Z (16:52 Bogotá), 18/20 venues**, and the local `unico/funding-rates/index.html` was rebuilt at 17:25. The live page stayed at Oct 24 9:51 only because the upload never ran after the gate failure.

3. **Latent timeout problem if the timer is simply re-enabled.**
   - `~/.config/systemd/user/echolike-funding-page.service` has `TimeoutStartSec=400`.
   - The script's own inner budgets are already bigger: screener `timeout 180` + directory QA `timeout 300` + click-through `timeout 480` + site audit `timeout 600`, plus page/test.
   - Journal on Oct 23 shows repeated `start operation timed out` after exactly 400 s (21:07→21:13, 22:07→22:13, 23:07→23:14). So an enabled timer can still be killed mid-gate, and a killed run never publishes.
   - Not a key/auth problem: no credential errors in the log; the run reached directory QA and click-through, which are after all data fetching.

## Status after Coco review (2026-10-25 19:50 Bogotá)

Staying stale is **intentional**: Nova asked on Oct 24 for all `echolike-*` services/timers to stay off until he says otherwise. Do **not** re-enable the timer or change the unit now. The timeout note below is kept for whenever Nova turns publishing back on. Also: echolike.app is moving to **GitHub Pages**, so `funding_publicar.sh`'s upload target (`operador/publicar_deed.py` → deed.page) may need updating in that same future pass; the screener/page-build part stays the same.

## Smallest fix (for the future; none of this was run)

1. Raise the service timeout **before** re-enabling, so one full gate pass fits:
   `~/.config/systemd/user/echolike-funding-page.service` → `TimeoutStartSec=1800` (or 1500; the current worst-case inner chain is >1,500 s).
   Then `systemctl --user daemon-reload`.
2. Start/enable the timer: `systemctl --user enable --now echolike-funding-page.timer`.
3. Watch one run: `journalctl --user -u echolike-funding-page.service -f` and `tail -f funding_publicar.log`; success ends with `upload http=200/201`, and the live page's Updated line should stop being Oct 24 9:51.

A code change is **not** required for the cause: the old click-through high (`home_missing_section private/progress/`) is already fixed in source/build (`64a9ab6`). The remaining change is operational (timeout + timer), and enabling services is Coco's call, so I did not create a branch, edit the unit, or start anything.

## Evidence paths
- `funding_publicar.log` (last run 2026-10-24 09:51–09:53)
- `reportes/recorrido_2026-10-24_funding.md` (1 high, home missing private/progress)
- `~/.config/systemd/user/echolike-funding-page.{service,timer}`
- `journalctl --user -u echolike-funding-page.{timer,service}`
- `estado/funding_publico.json`, `unico/funding-rates/index.html`
