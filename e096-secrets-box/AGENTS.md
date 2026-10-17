# e096 — Secrets box (PI WEB secret input that never touches the transcript)

The missing half of the vault RFC (`vault/RFC.md` §6, first checkbox): a PI WEB
panel where a secret is typed and stored, with the value never entering a chat
message, a session transcript, a log, argv, the environment or a temp file.

Read `spec.md` for the contract and `README.md` for what works today and what does
not. `vault/` is a fork of the `/tmp/night/vault` prototype with one addition: the
vault can now read the value and the passphrase from file descriptors
(`--value-fd`, `--passphrase-fd`), which is what makes the PI WEB path possible.

## Product

| Surface | User action |
|---|---|
| PI WEB workspace panel `Secrets` | Type a name, type the value (masked), type the vault passphrase, press **Store as NAME**; press **Refresh names** to list the secret names in the vault (never values). Status line confirms by name or shows a scrubbed error. |

## Layout

```
src/server.mjs          server peer: {name, value, passphrase} -> vault CLI (value on fd 0, passphrase on fd 3)
src/browser/index.js    workspace panel: password fields, cleared after use, name-only echo
needs.json              machine values (vault CLI path, vault file, backend) — no hardcoded paths in src/
vault/vault             patched vault prototype from vault/RFC.md (fd input path added)
vault/RFC.md            the design and threat model this implements
test/transcript-leak.test.mjs   canary test: the value is nowhere it must not be
test/panel.test.mjs             panel test: masked fields, cleared DOM, no logging
```

## Rules

- **Dummy values only in tests and in this repo.** Any value that appears in a test,
  a log, or a transcript is already public by construction.
- **Never log a secret.** The server peer must contain no `console.*` at all; a test
  fails if one is added.
- The value travels on a pipe (fd 0) and the passphrase on a second pipe (fd 3).
  Never argv, never env, never a temp file.
- Config comes from `needs.json` (`SECRETS_BOX_NEEDS` overrides the path for tests),
  never from constants in `src/`.
- The panel never renders a value, not even masked: names only.
- Run both suites before claiming anything works:
  `npm test` (node) and `npm run test:vault` (both crypto backends).

## Not yet true (do not sell it as true)

- The plugin is **not loaded** in the running daemon: PI WEB caches plugin code at
  daemon start, so enabling it needs a settings change plus a session-daemon restart
  (not done here — see README).
- The passphrase lives in the browser field while it is typed, and in the vault
  process memory while it runs. No memory hardening (see RFC §4).
- No rotation, deletion, audit log, or secret generation.
