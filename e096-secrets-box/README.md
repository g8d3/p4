# e096 — Secrets box

Type a secret into PI WEB and have it land in the encrypted vault — without the
value ever touching the chat, the session transcript, a log, argv, the environment or
a temp file. This is the PI WEB half of `vault/RFC.md` (its §6 first checkbox).

## What works today (tested)

```bash
npm test                 # 11 tests: transcript canary + panel behaviour
npm run test:vault       # the vault's own suite on both backends (openssl + age)
```

- `test/transcript-leak.test.mjs` pushes a random canary through the exact path the
  panel uses and asserts it is absent from the peer's response, from everything the
  process printed, from the child's `/proc/$$/cmdline` and `/proc/$$/environ`
  (recorded by a wrapper around the vault), from the vault file in cleartext, and
  from every `*.jsonl` under the workspace and `~/.pi-web`. Then it proves the value
  round-trips with the passphrase and fails with a wrong one.
- `test/panel.test.mjs` renders the real panel with a stub `html` tag: masked fields,
  cleared DOM after a store, name-only status, no logging, scrubbed error text.
- `vault/vault` gained `--value-fd` / `--passphrase-fd` (fd input instead of a TTY),
  and its original suite still passes on both backends.

## What does NOT work yet (be honest)

- **It is not loaded in the running daemon.** Enabling it needs the package path in
  PI WEB settings plus a `systemctl --user restart pi-web-sessiond` (PI WEB caches
  plugin code at daemon start), then a page reload. Not done here.
- The passphrase is typed in the browser and lives in the JS heap while in flight;
  the vault field is where the user keeps it. A per-session unlock in the peer would
  be better (spec.md §6.3).
- No delete/rotate/generate, no audit log, no memory hardening.

## Install (when you want it live)

```bash
# 1. check the config the plugin will use (vault CLI path, vault file, backend)
cat needs.json

# 2. register the package in PI WEB (settings → Pi packages / plugins: this directory)
#    plugin id: secrets-box  (defaultEnabled: false — enable it yourself)

# 3. the daemon caches plugin code at start
systemctl --user restart pi-web-sessiond
# then reload the page: a "Secrets" tab appears on the workspace panel
```

First use creates `vault_file` (default `~/.pi-vault.enc`) mode 0600, encrypted with
`age` if it is installed (it is: `~/.local/bin/age`), else the openssl fallback.

## Use

1. Open the workspace `Secrets` panel.
2. Name (`OPENAI_API_KEY`), value, vault passphrase → **Store as NAME**.
   The fields are cleared immediately, before the request even leaves the page.
3. **Refresh names** lists what is in the vault — names only, never values.
4. To use a secret in a process: `vault/vault exec ENV=NAME -- command` on your own
   TTY (the vault prompts; this panel is only for *input*).

## Why the value goes on descriptors and not on stdin text

`--value-fd 0` is stdin, and it is a pipe, not a here-string: nothing writes it to a
file, nothing shows it in `ps`, and no shell is involved (we `spawn` the CLI
directly). The passphrase takes a second pipe (fd 3) so that neither secret can be
confused with the other, and so the vault never has to read either from the
environment.

## Known risk that this does not remove

A secret pasted into the **chat** is in the transcript forever. If that has already
happened, rotate the secret at the issuer — do not try to scrub the log.
