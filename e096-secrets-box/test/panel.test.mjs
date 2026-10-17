// Panel-side tests for the secrets box: the browser module must not be able to
// leak the value either (no console, password fields, cleared DOM, name-only echo).
//
// The panel is rendered with a stub `html` tag and a stub document, so these run in
// plain node — no daemon, no browser, no build step.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import plugin from "../src/browser/index.js";

const ROOT = resolve(fileURLToPath(import.meta.url), "..", "..");
const LAST = { strings: [], values: [] };
// Stand-in for lit's html tag: records the parts (so a test can find the handler
// bound to a given element) and returns a flat string that keeps the interpolated
// values, so nested templates and status text are visible.
const html = (strings, ...values) => {
  LAST.strings = [...strings];
  LAST.values = [...values];
  return strings.reduce((acc, s, i) => acc + s + (i < values.length ? String(values[i] ?? "") : ""), "");
};

/** The value bound to @click on the button carrying this id. */
function clickHandler(id) {
  const idx = LAST.strings.findIndex((s) => s.includes(`id="${id}"`));
  assert.notEqual(idx, -1, `no button with id="${id}" in the render output`);
  for (let j = idx; j < LAST.strings.length; j++) {
    if (LAST.strings[j].trimEnd().endsWith("@click=")) return LAST.values[j];
  }
  throw new Error(`no @click handler after id="${id}"`);
}

/** Everything the panel rendered, as one string (status text included). */
function renderedText() {
  return LAST.strings.reduce((acc, s, i) => acc + s + (i < LAST.values.length ? String(LAST.values[i] ?? "") : ""), "");
}

function fakeDocument() {
  return {
    createElement: () => ({
      type: "", placeholder: "", autocomplete: "", spellcheck: true, value: "",
    }),
  };
}

function fakeContext(peer, host = { requestRender() {} }) {
  return {
    machine: { id: "m1" },
    workspace: { id: "w1", projectId: "p1" },
    peer,
    host,
  };
}

test("render: value and passphrase fields are password inputs, never plain text", () => {
  globalThis.document = fakeDocument();
  const panel = plugin.activate({ html });
  const ctx = fakeContext({ request: async () => ({ ok: true, name: "X" }) });
  const out = panel.contributions.workspacePanels[0].render(ctx);
  assert.equal(typeof out, "string");
  const f = ctx.host.__sbFields;
  assert.equal(f.value.type, "password", "the secret field must be type=password");
  assert.equal(f.passphrase.type, "password", "the passphrase field must be type=password");
  assert.equal(f.name.type, "text");
  assert.equal(f.value.autocomplete, "new-password");
  assert.equal(f.passphrase.autocomplete, "new-password");
  assert.equal(f.value.spellcheck, false);
});

test("store: the peer gets the secret, the page keeps none of it", async () => {
  globalThis.document = fakeDocument();
  const calls = [];
  const printed = [];
  const origLog = console.log;
  console.log = (...a) => printed.push(a.join(" "));
  const panel = plugin.activate({ html });
  const ctx = fakeContext({
    request: async (op, input) => {
      calls.push({ op, input });
      return { ok: true, name: input.name, backend: "age" };
    },
  });
  panel.contributions.workspacePanels[0].render(ctx);
  ctx.host.__sbFields.name.value = "MY_KEY";
  ctx.host.__sbFields.value.value = "canary-value-abc";
  ctx.host.__sbFields.passphrase.value = "canary-passphrase-abc";

  await clickHandler("sb-store")();
  console.log = origLog;

  assert.equal(calls.length, 1);
  assert.equal(calls[0].op, "store");
  assert.deepEqual(calls[0].input, { name: "MY_KEY", value: "canary-value-abc", passphrase: "canary-passphrase-abc" });

  // the DOM no longer holds either secret
  assert.equal(ctx.host.__sbFields.value.value, "", "the value stayed in the page after storing");
  assert.equal(ctx.host.__sbFields.passphrase.value, "", "the passphrase stayed in the page");

  // the rendered status names the secret and nothing else
  panel.contributions.workspacePanels[0].render(ctx);
  const text = renderedText();
  assert.ok(text.includes("MY_KEY"), "the status should confirm by name");
  assert.ok(!text.includes("canary-value-abc"), "the status echoed the value");
  assert.ok(!text.includes("canary-passphrase-abc"), "the status echoed the passphrase");
  assert.deepEqual(printed, [], "the panel must not log anything");
});

test("store failure: the error is shown, the secret is not", async () => {
  globalThis.document = fakeDocument();
  const panel = plugin.activate({ html });
  const ctx = fakeContext({ request: async () => ({ ok: false, error: "vault: error: decrypt failed" }) });
  panel.contributions.workspacePanels[0].render(ctx);
  ctx.host.__sbFields.name.value = "K";
  ctx.host.__sbFields.value.value = "canary-fail-value";
  ctx.host.__sbFields.passphrase.value = "canary-fail-pass";
  await clickHandler("sb-store")();
  panel.contributions.workspacePanels[0].render(ctx);
  const text = renderedText();
  assert.ok(text.includes("decrypt failed"), "the error should be visible");
  assert.ok(!text.includes("canary-fail-value") && !text.includes("canary-fail-pass"), "an error must not echo secrets");
  assert.equal(ctx.host.__sbFields.value.value, "");
});

test("list: names are rendered, values are not", async () => {
  globalThis.document = fakeDocument();
  const panel = plugin.activate({ html });
  const ctx = fakeContext({ request: async () => ({ ok: true, names: ["A_KEY", "B_KEY"] }) });
  panel.contributions.workspacePanels[0].render(ctx);
  ctx.host.__sbFields.passphrase.value = "canary-list-pass";
  await clickHandler("sb-list")();
  panel.contributions.workspacePanels[0].render(ctx);
  const text = renderedText();
  assert.ok(text.includes("A_KEY") && text.includes("B_KEY"), "names should be listed");
  assert.ok(!text.includes("canary-list-pass"), "the passphrase was rendered back");
  assert.equal(ctx.host.__sbFields.passphrase.value, "", "the passphrase should be cleared after a read");
});

test("policy: the browser module never logs and never asks for a plain-text secret field", () => {
  const src = readFileSync(resolve(ROOT, "src", "browser", "index.js"), "utf8");
  const logs = src.match(/console\.\w+/g) ?? [];
  assert.deepEqual(logs, [], `browser/index.js must not log (found ${logs.join(", ")})`);
  assert.ok(src.includes('fields.value.type = "password"'));
  assert.ok(src.includes('autocomplete = "new-password"'));
  assert.ok(!/type\s*=\s*"text"[^\n]*secret/i.test(src), "the secret field must not be a text input");
});
