// Model list guard: keeps pi's enabledModels from being silently collapsed.
//
// The failure this exists for (observed 2026-10-30): `pi install` rewrote
// ~/.pi/agent/settings.json and replaced a 107-entry enabledModels list with 3 entries.
// Nothing warned; the user only noticed missing models later. This guard keeps a canonical
// snapshot and repairs the signature of that bug: a list that SHRANK A LOT and is a subset
// of what was there. It deliberately does not fight a deliberate edit: removing one or two
// models by hand is your call and is never "repaired".
//
// Settings path can be overridden with P4_PI_SETTINGS (tests, other profiles).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const SETTINGS = process.env.P4_PI_SETTINGS || path.join(os.homedir(), ".pi", "agent", "settings.json");
const DATA = path.join(process.env.PI_WEB_DATA_DIR || path.join(os.homedir(), ".pi-web"),
                       "plugin-data", "p4-models");
const CANON = path.join(DATA, "canonical.json");
const DRIFT = path.join(DATA, "drift.jsonl");
const MIN_DROP = 5;          // a drop of 5+ models is the collapse signature, not an edit
const CHECK_MS = 60_000;

function readJSON(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return fallback; }
}
function writeJSON(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(value, null, 2) + "\n");
  fs.renameSync(tmp, file);
}
function note(entry) {
  try {
    fs.mkdirSync(DATA, { recursive: true });
    fs.appendFileSync(DRIFT, JSON.stringify({ at: new Date().toISOString(), ...entry }) + "\n");
  } catch { /* a log line must never break the daemon */ }
}

export function classify(current, canonical) {
  const now = current || [];
  const want = canonical || [];
  const missing = want.filter((m) => !now.includes(m));
  const subset = now.every((m) => want.includes(m));
  const drop = want.length - now.length;
  return {
    count: now.length,
    canonicalCount: want.length,
    missing,
    drop,
    // the bug's signature: it collapsed, and it collapsed into a subset of what we knew
    collapsed: drop >= MIN_DROP && subset && now.length > 0,
    shrunk: drop > 0,
  };
}

export function check({ repair = true } = {}) {
  const settings = readJSON(SETTINGS, null);
  if (!settings) return { ok: false, error: `cannot read ${SETTINGS}` };
  const current = settings.enabledModels || [];
  let canon = readJSON(CANON, null);
  if (!canon || !Array.isArray(canon.enabledModels) || canon.enabledModels.length < current.length) {
    // first run, or the list legitimately grew: that becomes the new known-good
    canon = { enabledModels: current, defaultProvider: settings.defaultProvider || null,
              defaultModel: settings.defaultModel || null, savedAt: new Date().toISOString() };
    writeJSON(CANON, canon);
    return { ok: true, action: "snapshot", count: current.length };
  }
  const verdict = classify(current, canon.enabledModels);
  if (!verdict.collapsed) return { ok: true, action: "none", ...verdict };
  const restored = [...new Set([...canon.enabledModels, ...current])];
  if (repair) {
    const backup = path.join(DATA, `settings-before-repair-${Date.now()}.json`);
    fs.mkdirSync(DATA, { recursive: true });
    fs.copyFileSync(SETTINGS, backup);
    settings.enabledModels = restored;
    writeJSON(SETTINGS, settings);
    note({ event: "repaired", had: current.length, restoredTo: restored.length, backup });
  }
  return { ok: true, action: repair ? "repaired" : "would-repair", ...verdict, restoredTo: restored.length };
}

export function report() {
  const settings = readJSON(SETTINGS, {});
  const canon = readJSON(CANON, null);
  const events = [];
  try {
    for (const line of fs.readFileSync(DRIFT, "utf8").split("\n")) {
      if (line.trim()) { try { events.push(JSON.parse(line)); } catch { /* skip */ } }
    }
  } catch { /* none yet */ }
  const current = settings.enabledModels || [];
  const verdict = classify(current, (canon && canon.enabledModels) || []);
  return {
    settings: SETTINGS,
    count: current.length,
    canonicalCount: verdict.canonicalCount,
    savedAt: (canon && canon.savedAt) || null,
    defaultProvider: settings.defaultProvider || null,
    defaultModel: settings.defaultModel || null,
    drop: verdict.drop,
    minDrop: MIN_DROP,
    events: events.slice(-20).reverse(),
    models: current,
  };
}

export function startGuard() {
  try { check(); } catch { /* ignore */ }
  const timer = setInterval(() => { try { check(); } catch { /* ignore */ } }, CHECK_MS);
  timer.unref?.();
  return () => clearInterval(timer);
}
