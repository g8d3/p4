# Contract — secret input that bypasses the transcript

Status: **prototype, tested, not enabled in the live daemon.** Dummy values only.

## 1. The invariant

> A value typed into the Secrets panel reaches the encrypted vault without ever
> being written to a session transcript, a log, a process argument, the environment,
> or a temporary file.

Everything else in this document is a mechanism in service of that sentence, and
each clause has a test that fails if it stops being true.

## 2. Path

```
browser panel (password field)
   │  context.peer.request("store", {name, value, passphrase})
   ▼
server peer  src/server.mjs
   │  spawn(vault, ["set", NAME, "--value-fd", "0", "--passphrase-fd", "3"])
   │      stdin  (fd 0) ← value
   │      fd 3          ← passphrase
   ▼
vault CLI (vault/vault)
   │  reads both from the descriptors, encrypts the whole store
   ▼
vault file (mode 0600, age or openssl; never cleartext)
```

Why descriptors: argv is visible in `ps` and shell history, the environment is
visible in `/proc/<pid>/environ` to the same user, a temp file outlives the process
on disk, and the chat/transcript path is exactly what we are removing. A pipe has
none of those properties.

## 3. Clauses, and the test that enforces each

| clause | where | test |
|---|---|---|
| the value is not in the peer's response | `src/server.mjs` returns `{ok, name}` only | `transcript-leak.test.mjs` "store: the value round-trips" |
| the value is not in any process output | no `console.*` in the peer | "policy: the server module never logs" + captured output |
| the value is not in the child's argv or env | `--value-fd 0`, `--passphrase-fd 3` | "the value is nowhere it must not be" (wrapper records `/proc/$$/cmdline` and `/proc/$$/environ`) |
| the value is not cleartext on disk | vault encrypts the whole store | same test: file is mode 0600 and does not contain the canary |
| the value is not in a transcript | the peer is not a chat turn | same test: greps every `*.jsonl` under the workspace, `~/.pi-web` and the experiment dir |
| the value is recoverable | vault `get` with the passphrase | "the value is recoverable, and the passphrase is the gate" |
| a wrong or empty passphrase fails | vault decrypt | same test |
| names are listed, values never | peer `list` returns `names` | "list: names come back, values never do" |
| errors never echo a secret | `scrub()` removes value and passphrase from error text | "list" (wrong passphrase) + "empty input is refused" |
| the panel never renders or logs a value | panel renders names and status only | `panel.test.mjs` (all cases) |
| the value does not linger in the page | fields are cleared before the request and after | "store: the peer gets the secret, the page keeps none of it" |
| the secret field is masked | `type="password"`, `autocomplete="new-password"` | "render: value and passphrase fields are password inputs" |

## 4. Threat model

Inherited from `vault/RFC.md` §3–4 and unchanged: compromised endpoint, memory
forensics, a hostile child process, weak/lost passphrases and multi-user sharing are
out of scope. Two additions specific to this path:

- **The browser is trusted.** The value exists in the DOM until it is cleared, in the
  JS heap while the request is in flight, and in the passphrase field while the user
  types. Browser extensions, devtools and XSS can read all three. This panel removes
  the *transcript* exposure, not the endpoint exposure.
- **The PI WEB server is trusted.** The browser-to-peer hop is a local, same-origin
  request handled in-process; nothing is persisted on the way. The peer holds the
  value in memory only long enough to write it to the child's stdin.

## 5. Deliberate non-goals in this prototype

- No `delete`, `rotate`, `gen` or audit log (RFC §6 keeps them open).
- No client-side confirmation of the value (the vault cannot compare what it never
  sees twice, and asking for it twice would double the time the value spends in the
  browser).
- No OpenSSL hardening: it remains the fallback, unauthenticated (RFC §6).
- Not loaded into the running daemon; enabling it is a deliberate human step
  (`needs.json` + settings + session-daemon restart).

## 6. Review notes for a human

1. Read `src/server.mjs` first: it is 150 lines and it is the only place a value
   crosses a process boundary.
2. Run `npm test` and watch the canary assertions specifically.
3. Then decide whether the passphrase belongs in the browser at all, or whether the
   vault should be unlocked per session by the peer (bigger change, no browser
   custody of the passphrase, needs a lock/unlock UX).
