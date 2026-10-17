# RFC: secrets vault for Pi / PI WEB

Status: **prototype + RFC** (`/tmp/night/vault/`). Not production.
Design below is fixed per the request; this document records it.

## 1. Problem

Pasting a secret into the chat leaves it in the transcript JSONL in
cleartext. From there it spreads: session logs, relay packets, backups,
quotes in follow-up prompts. The secret's lifetime becomes the lifetime of
every copy of the transcript, on machines the user never chose to trust
with it.

Requirements for the fix:

- Secret input must **bypass the transcript entirely**.
- Secrets at rest must be **encrypted**, never cleartext files.
- Normal display must be **masked** (names, never values).
- A secret reaches only **the process that needs it**, as ambient env, and
  nowhere else.
- A **ceremony** the user can follow without understanding crypto, where
  the agent provably never touches real secret material.

## 2. Design (fixed)

1. **Transcript-bypassing input.**
   - Terminal: read value and passphrase from `/dev/tty` with echo
     disabled (`getpass`). Nothing secret ever comes from argv (argv leaks
     to shell history, `ps`, transcripts) or from chat text.
   - PI WEB: a password-type field whose content goes directly to the vault
     layer and is never inserted into the message/transcript stream.
     (Contract only in this prototype — no PI WEB code is shipped, see §6.)
2. **Encrypted vault on disk.** One file (default `~/.pi-vault.enc`,
   override `$VAULT_FILE`), mode 0600, containing a JSON object
   `{name: value}` encrypted as a whole:
   - Preferred: `age` (XChaCha20-Poly1305 + scrypt), passphrase handled
     entirely by the `age` binary on `/dev/tty` — our code never sees it.
     (Test-only exception: when `$VAULT_PASSPHRASE` is set, the CLI feeds
     that dummy passphrase to age's TTY prompts through a pty so
     `test.sh` round-trips without a human at a terminal.)
   - Fallback: OpenSSL `AES-256-CBC + PBKDF2`
     (100k iterations, salt). Passphrase reaches `openssl` via environment,
     never argv. Selected automatically when `command -v age` fails.
3. **Masked display.** `list` prints secret *names* only, sorted, one per
   line. No command prints values except `get` (raw stdout, for piping —
   with a stderr warning), and `exec` prints nothing itself.
4. **Env-only injection.** `vault exec ENVVAR=NAME [...] -- CMD...`
   decrypts in memory and spawns exactly one child with the mapped variables
   added to its environment. The parent never prints them; the test hook is
   explicitly unset in the child's environment.
5. **Ceremony + agent hands-off.** The user custodians the passphrase and
   types all real secrets on their own TTY. The agent works only with dummy
   values in tests (`VAULT_TEST_VALUE`, isolated temp file, deleted
   afterwards). See §5.

CLI surface (minimal, complete): `vault set NAME | get NAME | list |
exec ENV=NAME [...] -- CMD...`, plus `--file` / `--backend` overrides.
Config lives in env documented in `needs.json`, not in code.

## 3. Threat model — what this covers

- Casual transcript/log exposure of pasted secrets (the motivating bug).
- Shoulder-surfing / screen-share of TTY input (echo off).
- Cleartext secrets on disk (encrypted at rest, 0600).
- Accidental display (`list` never shows values; `get` warns).
- `ps` / shell-history capture (nothing secret in argv; passphrase to
  `openssl` via env).
- Agent-side retention: tests use dummy values only, so transcripts, relay
  packets, and logs from development contain no real secrets.

## 4. Threats explicitly OUT of scope (non-goals for this prototype)

- **Compromised endpoint:** root/malware on the user's machine reads TTY,
  env, and RAM regardless of this design. Out of scope.
- **Memory forensics / swap / core dumps:** plaintext exists in process
  memory during encrypt/decrypt/exec; no `mlock`, no zeroing guarantees
  (best-effort overwrite of temp plaintext files only).
- **Child-process hygiene:** `vault exec` cannot stop `CMD` from logging,
  echoing, or exfiltrating its own env. The child is fully trusted.
- **Env leakage past exec:** `/proc/<pid>/environ` (same user), crash
  reporters, and verbose process managers can still expose the child's env.
- **Passphrase strength / loss:** weak passphrases are brute-forcible
  (especially the OpenSSL fallback); a lost passphrase means total loss —
  there is no recovery, by design.
- **Vault file integrity beyond decryption:** no versioning, no audit log,
  no tamper-evidence beyond "decrypt fails".
- **Multi-user / ACLs / rotation / sharing:** single-user file, no access
  control, no rotation or revocation story.
- **PI WEB transport/front-end:** the password-field contract is specified
  (§2.1) but not implemented or reviewed here; XSS, devtools, or a logging
  proxy in front of PI WEB would re-expose the secret.
- **OpenSSL-fallback crypto limits:** AES-CBC has no authentication beyond
  padding; PBKDF2-100k is modest. Documented as fallback, not the goal —
  `age` remains the preferred backend.

## 5. Ceremony (normative for real use)

1. The user chooses a strong vault passphrase and never shares it. The
   agent must never ask for it and must refuse pasted secrets
   ("don't paste it in chat — use `vault set NAME` on your terminal").
2. Storing: user runs `vault set NAME` on their own TTY and types the
   value twice (echo off). The agent looks away: no screen, no copy.
3. Using: user runs `vault exec ENVVAR=NAME -- command` on their own TTY,
   typing the passphrase when prompted (echo off). The secret exists only
   in that child's environment.
4. Viewing is discouraged: `vault get NAME` is for piping, not for eyes;
   its output must never be pasted into chat, tickets, or docs.
5. Agent rule: the agent NEVER handles real secrets. All agent-run tests
   use `test.sh` with dummy values, an isolated `$VAULT_FILE` in a temp
   dir, and cleanup. Any transcript containing a value from `test.sh` is
   safe by construction (dummies are public).
6. Breach rule: if a real secret ever enters chat/transcript, treat it as
   compromised — rotate it at the issuer, do not try to "delete it from
   the log".

## 6. What is missing for production

- [ ] PI WEB password field: implement the direct-to-vault path, with a
      test proving the value never enters the transcript JSONL, plus
      front-end review (no logging, no autocomplete, no devtools echo).
- [x] Make `age` the tested path: `age` 1.1.1 installed at
      `~/.local/bin/age`; `test.sh` exercises encrypt/decrypt round-trip
      (set/list/get/exec/wrong-passphrase) for BOTH backends. Done
      2026-10-17. Remaining: demote OpenSSL to legacy-read-only.
- [ ] Authenticated encryption everywhere (age already is; kill or upgrade
      the CBC fallback — at minimum add HMAC, ideally remove it).
- [ ] Memory hygiene: `mlock`/no-swap handling, zeroing buffers, no temp
      plaintext files (stream through pipes).
- [ ] Lock-out / wrong-passphrase throttling, atomic writes + backups,
      `delete`/`rename` commands, audit log (names + timestamps only).
- [ ] Secret generation (`vault gen NAME --length 32`) so high-entropy
      values never cross a human at all.
- [ ] Child-env hardening guidance (hide `/proc`, warn on `set -x`,
      discourage `printenv` debugging with real vaults).
- [ ] Independent crypto review before any real-secret reliance.

## Appendix: verification log (this environment)

- `command -v age` → `~/.local/bin/age`, version 1.1.1 → `auto` backend
  now selects `age`; OpenSSL remains as fallback.
- `openssl version` → OpenSSL 3.0.13.
- `test.sh` (dummy values only) covers BOTH backends on isolated temp
  vault files: set → encrypted file (0600, no cleartext; age file header
  `age-encryption.org/v1` + scrypt) → list (names only) → get (exact
  round-trip) → unknown-name failure → exec (env injection, silent on
  `true`) → wrong-passphrase failure → sorted two-name list → cleanup.
  All green on 2026-10-17 (openssl block + age block).
- age test-mode mechanism: real use keeps the passphrase inside the `age`
  binary on /dev/tty (code never sees it); only when `$VAULT_PASSPHRASE`
  is set (tests, dummies only) the CLI feeds it to age's TTY prompts
  through a pty (stdlib `pty` module). Previously the age backend failed
  without a human at a terminal (`age: standard input is not a terminal,
  and /dev/tty is not available`); fixed 2026-10-17, see `vault` source.
