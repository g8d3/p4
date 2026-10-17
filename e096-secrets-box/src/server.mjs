// Server peer for the Secrets box.
//
// Job: take {name, value, passphrase} from the browser panel and hand them to the
// vault CLI, which encrypts them at rest. Three rules, in order of importance:
//
//   1. The value never enters the transcript. This module is a PI WEB server peer,
//      not a chat turn: nothing it receives is written to a session JSONL. It also
//      never logs, never echoes, and strips the value/passphrase from any error
//      text it returns.
//   2. The value never reaches argv, the environment or a temp file: it goes to
//      the vault over a pipe (`--value-fd 0`), and the passphrase over a second
//      pipe (`--passphrase-fd 3`). `ps` and /proc/<pid>/environ stay clean.
//   3. The panel gets back only `{ok, name}` (or an error message with the secrets
//      scrubbed out) — never the value.
//
// Config (vault path, backend) comes from needs.json, never from constants here.

import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const NAME_RE = /^[A-Za-z_][A-Za-z0-9_.-]{0,63}$/;

let needsCache;

/** Load needs.json (path overridable for tests via $SECRETS_BOX_NEEDS). */
export function needs() {
  if (!needsCache) {
    const path = process.env.SECRETS_BOX_NEEDS || join(HERE, "..", "needs.json");
    needsCache = JSON.parse(readFileSync(path, "utf8"));
  }
  return needsCache;
}

/** Remove every occurrence of the given secrets from a string. */
export function scrub(text, secrets) {
  let out = String(text ?? "");
  for (const secret of secrets) {
    if (typeof secret === "string" && secret.length > 0) {
      out = out.split(secret).join("[redacted]");
    }
  }
  return out;
}

/**
 * Run the vault with the value on stdin (fd 0) and the passphrase on fd 3.
 * Resolves with {code, stdout, stderr}; never throws on a non-zero exit.
 */
export function runVault(args, { value = "", passphrase = "" } = {}) {
  const { vault_cli, vault_file, vault_backend } = needs();
  return new Promise((resolve) => {
    const child = spawn(vault_cli, args, {
      // fd 3 is the passphrase pipe. Neither secret is in argv or env.
      stdio: ["pipe", "pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        VAULT_FILE: vault_file,
        VAULT_BACKEND: vault_backend,
        // never inherit a test-hook passphrase: the fd is the only channel
        VAULT_PASSPHRASE: "",
        VAULT_TEST_VALUE: "",
      },
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("error", (err) => resolve({ code: -1, stdout, stderr: String(err) }));
    child.on("close", (code) => resolve({ code: code ?? -1, stdout, stderr }));
    child.stdin.end(value);
    child.stdio[3].end(passphrase);
  });
}

function lastMeaningfulLine(text) {
  const lines = String(text ?? "").split("\n").map((l) => l.trim()).filter(Boolean);
  return lines.length ? lines[lines.length - 1] : "";
}

function asString(v) {
  return typeof v === "string" ? v : "";
}

/**
 * Handle one peer operation. Exported for tests (the daemon calls it through the
 * plugin's activate() below).
 */
export async function handleOperation(operation, input) {
  const name = asString(input?.name).trim();
  const value = asString(input?.value);
  const passphrase = asString(input?.passphrase);

  if (operation === "store") {
    if (!NAME_RE.test(name)) {
      return { ok: false, error: "name must match [A-Za-z_][A-Za-z0-9_.-]{0,63}" };
    }
    if (!value) return { ok: false, error: "value is empty, nothing stored" };
    if (!passphrase) return { ok: false, error: "passphrase is empty, nothing stored" };
    const r = await runVault(["set", name, "--value-fd", "0", "--passphrase-fd", "3"], { value, passphrase });
    if (r.code !== 0) {
      return {
        ok: false,
        name,
        // scrub: a vault/age error must never carry the secret back to the panel
        error: scrub(lastMeaningfulLine(r.stderr) || `vault exited ${r.code}`, [value, passphrase]),
      };
    }
    return { ok: true, name, backend: needs().vault_backend };
  }

  if (operation === "list") {
    if (!passphrase) return { ok: false, error: "passphrase is empty, cannot read the vault" };
    const r = await runVault(["list", "--passphrase-fd", "3"], { passphrase });
    if (r.code !== 0) {
      return { ok: false, error: scrub(lastMeaningfulLine(r.stderr) || `vault exited ${r.code}`, [passphrase]) };
    }
    const names = r.stdout.split("\n").map((l) => l.trim()).filter(Boolean);
    return { ok: true, names };
  }

  throw new Error(`Unknown secrets-box operation: ${operation}`);
}

const plugin = {
  apiVersion: 3,
  name: "Secrets box",
  activate() {
    return {
      peer: {
        async request(context) {
          context.signal.throwIfAborted();
          return handleOperation(context.operation, context.input);
        },
      },
    };
  },
};

export default plugin;
