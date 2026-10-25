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
