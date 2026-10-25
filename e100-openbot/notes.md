# e100-openbot — status

## Done
- Downloaded OpenBot Linux AppImage (0.49.0, x86_64, ~297MB) to `downloads/`.
- Verified it boots headless under Xvfb: first-run screen = language picker (see `first-run.png`).
- Verified default proxy is reachable: `$OPENCODE_GO_BASE_URL` + `models` -> HTTP 200 with `$OPENCODE_GO_API_KEY`.
- App requires OpenBot account sign-in before providers can be connected (log: `http/401/unauthorized: Sign in is required`).

## Wiring (when signed in)
- Provider type: OpenAI-compatible endpoint.
- Base URL: value of `OPENCODE_GO_BASE_URL`.
- API key: value of `OPENCODE_GO_API_KEY`.
- Model: value of `OPENCODE_GO_MODEL`.
- Never paste key values into files; reference env names only.

## Next (needs user)
- Sign in to OpenBot (email code) — interactive, cannot do autonomously.
- Then connect the OpenAI-compatible endpoint with the values above and create the first agent.

## Test result (Oct 24, ~19:48 local)
- Agent "Tester" created with OpenCode/Flint 40B Free (no key needed).
- Greeting round-trip OK ("Hey! I'm Tester...").
- Task round-trip OK: asked "Reply with exactly the word READY" -> got "READY".
- Free tier: READY. OpenCode Go key (paid models incl. muse-spark-1.2-contributor): BLOCKED —
  "System secret storage is unavailable" (headless box, Login keyring locked,
  fresh keyrings can't be confirmed without a prompter). Fix on a desktop with
  a keyring, or relaunch with --password-store=basic (costs a new email code).

## Go-model findings (Oct 24, ~20:00 local)
- CLI proof: `opencode run --model opencode-go/muse-spark-1.3-contributor` -> "CLI-OK".
  Default credentials + 1.3 work end to end; `opencode models opencode-go` lists both
  muse-spark-1.2 and 1.3-contributor.
- OpenBot wraps the SYSTEM opencode CLI (log: source=system, 1.19.3, 1090 models probed)
  and hides paid models until the GUI Go key is saved. Model search for "muse-spark"
  in-app returns "No models match your search".
- Key save still fails: `app:set-provider-api-key: System secret storage is unavailable`,
  even with --password-store=basic. Agent model lives in openbot.db projection_agents
  (provider=opencode, model=opencode/flint-40b-free) — not touched to avoid breaking Tester.
- Unblocks instantly on any machine with a working keyring (one paste:
  Server settings -> Providers -> OpenCode -> Add key).

## Secret-storage: exhaustive result (Oct 24, ~20:00 local)
Tried, all failed with `app:set-provider-api-key: System secret storage is unavailable`:
1. Stock launch (no keyring at all).
2. gnome-keyring-daemon on session bus, user data dir (Login collection locked, password unknown — correctly out of reach).
3. Fresh XDG_DATA_HOME + --login with empty stdin (creates nothing usable; non---start daemons never own org.freedesktop.secrets on the bus).
4. --start daemon (owns the bus name) + CreateCollection via D-Bus (returns a prompt object; gnome-keyring renders NO dialog without a desktop prompter, so it can never be answered headless).
5. Fresh profile + --password-store=basic from first boot (flag confirmed in cmdline; still fails — this Electron build cannot do safeStorage here, period).
Visibility was never the issue: every X client enumerated (xlsclients/xdotool), every state screenshotted — no hidden window ever existed. The wall is cryptographic (unknown password), not visual.
Consequence: OpenBot sessions also don't survive restarts here (session token lives in secret storage) — each restart costs one email code. On any keyring'd machine all of this just works.
Tester recreated on the fresh profile (free model, greeted 8:05 PM).
Backup of first profile (Tester history): ~/.config/OpenBot.bak-firstrun

## FIXED: secret storage headless (Oct 24, ~20:40 Bogotá)
Root cause: the app itself calls `app.commandLine.appendSwitch("password-store", "gnome-libsecret")`
when there is no known desktop (found in resources/app.asar), so `--password-store=basic` is overridden,
and `safeStorage.isEncryptionAvailable()` needs an unlocked `default` collection on the session bus.
Fix = OpenBot's own recipe (resources/hosting/openbot-container): random password file ->
`gnome-keyring-daemon --unlock --components=secrets < pwfile` (creates + unlocks `login` with no prompter),
then `--start`, and `keyrings/default` containing `login`. All in a dedicated dbus-launch session with
XDG_DATA_HOME=.keyring-data (gitignored). Nova's ~/.local/share/keyrings untouched.
- Launch / restart: `bin/launch.sh` (kills old app + its dbus/keyring, starts fresh, writes `.keyring-state/env`).
- Signed in as hello@echolike.app (code read from ~/code/p4/e092-echolike/correo/inbox via `bin/entercode.py`).
- OpenCode Go key saved (Server settings > Providers > OpenCode > Add key; `bin/setkey.py`, key from env).
- Tester switched to OpenCode Go/DeepSeek V4.1 Flash; "Reply with exactly GO-OK" -> "GO-OK".
- Restart via launch.sh: still signed in as hello@echolike.app, "Key saved" persisted.
- Mobile: Settings > Mobile Connect > 2.1 "Generate QR code" (one-time, 2 min, single use);
  `bin/qr.py` regenerates and screenshots just the QR to /tmp/openbot_qr.png. 2.2 offers a permanent link (not generated).
- obctl.py now prefers the index.html page target (a "Team WebRTC" page appears after Mobile Connect).
- Helpers: bin/ui.py (click by label + dump), bin/rclick.py (real CDP mouse click, needed for Radix popovers),
  bin/pick.py (choose model in picker), bin/send.py (send a chat message).

## Fast phone QR
Run `bin/qr_now.sh` on the mini PC: it opens Settings > Mobile Connect, generates a one-time code and saves `/tmp/openbot_qr.png` (~10 s). From another machine: `ssh minipc ~/code/p4/e100-openbot/bin/qr_now.sh && scp minipc:/tmp/openbot_qr.png .`
Codes last 2 minutes and work once. For a phone you trust long-term, "Generate link" (permanent link) avoids QR codes but anyone with it can sign in.
