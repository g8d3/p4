// Model list guard: keeps YOUR picks in pi's enabledModels list.
//
// Your picks live in wanted.json (see docs/current-models.md). The guard's only job:
// if a pick is missing from ~/.pi/agent/settings.json, put it back and log it.
// It never removes anything, and it never changes wanted.json by itself.
//
// Why explicit instead of automatic: the first version kept a canonical.json
// snapshot that silently grew to 162 models and "repaired" any drop of 5+. On
// 2026-10-30 that logic rewrote a deliberate 4-model edit back to 162 models
// twice in one minute. A heuristic cannot tell a collapse from a decision;
// an explicit list can. canonical.json is retired (kept on disk as history).
//
// wanted.json shape: { "models": ["provider/id", ...], "savedAt": "<iso>" }
// Paths can be overridden for tests: P4_PI_SETTINGS, PI_WEB_DATA_DIR.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const SETTINGS = process.env.P4_PI_SETTINGS || path.join(os.homedir(), ".pi", "agent", "settings.json");
// Backend identity: proves in the panel which daemon serves this report —
// the pid/startedAt change on every session-daemon restart.
const BOOT_AT = new Date().toISOString();
const DATA = path.join(process.env.PI_WEB_DATA_DIR || path.join(os.homedir(), ".pi-web"),
                       "plugin-data", "p4-models");
const WANTED = path.join(DATA, "wanted.json");
const DRIFT = path.join(DATA, "drift.jsonl");
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

export function readWanted() {
  const w = readJSON(WANTED, null);
  if (!w || !Array.isArray(w.models)) return null;
  return { models: [...new Set(w.models)], savedAt: w.savedAt || null };
}

// Kept for callers that used the old heuristic API: now a plain diff against
// the explicit picks. `collapsed` is true only when picks are missing.
export function classify(current, wanted) {
  const now = current || [];
  const want = wanted || [];
  const missing = want.filter((m) => !now.includes(m));
  const extras = now.filter((m) => !want.includes(m));
  return {
    count: now.length,
    wantedCount: want.length,
    canonicalCount: want.length,
    missing,
    extras,
    drop: missing.length,
    shrunk: missing.length > 0,
    collapsed: missing.length > 0,
  };
}

export function check({ repair = true } = {}) {
  const settings = readJSON(SETTINGS, null);
  if (!settings) return { ok: false, error: `cannot read ${SETTINGS}` };
  const wanted = readWanted();
  // No picks recorded yet: do nothing. The old code snapshotted whatever was
  // biggest on first run, which is how 162 models of provider bloat became
  // "known good". Recording picks is an explicit act (scripts/models.py).
  if (!wanted) return { ok: true, action: "no-wanted", count: (settings.enabledModels || []).length };
  const current = settings.enabledModels || [];
  const missing = wanted.models.filter((m) => !current.includes(m));
  if (missing.length === 0) {
    return { ok: true, action: "none", count: current.length, wantedCount: wanted.models.length,
             extras: current.length - wanted.models.length };
  }
  // Put back exactly the missing picks, keep everything else in place.
  const restored = [...current, ...missing];
  if (repair) {
    const backup = path.join(DATA, `settings-before-repair-${Date.now()}.json`);
    fs.mkdirSync(DATA, { recursive: true });
    fs.copyFileSync(SETTINGS, backup);
    settings.enabledModels = restored;
    writeJSON(SETTINGS, settings);
    note({ event: "repaired", had: current.length, missing, restoredTo: restored.length, backup });
  }
  return { ok: true, action: repair ? "repaired" : "would-repair", count: current.length,
           wantedCount: wanted.models.length, missing, restoredTo: restored.length };
}

export function report() {
  const settings = readJSON(SETTINGS, {});
  const wanted = readWanted();
  const events = [];
  try {
    for (const line of fs.readFileSync(DRIFT, "utf8").split("\n")) {
      if (line.trim()) { try { events.push(JSON.parse(line)); } catch { /* skip */ } }
    }
  } catch { /* none yet */ }
  const current = settings.enabledModels || [];
  const want = (wanted && wanted.models) || [];
  const verdict = classify(current, want);
  return {
    settings: SETTINGS,
    wantedFile: WANTED,
    hasWanted: Boolean(wanted),
    wantedSavedAt: (wanted && wanted.savedAt) || null,
    count: current.length,
    wantedCount: want.length,
    canonicalCount: want.length,
    savedAt: (wanted && wanted.savedAt) || null,
    defaultProvider: settings.defaultProvider || null,
    defaultModel: settings.defaultModel || null,
    backend: { pid: process.pid, startedAt: BOOT_AT },
    missing: verdict.missing,
    extras: verdict.extras,
    events: events.slice(-20).reverse(),
    models: current,
    wanted: want,
  };
}

export function startGuard() {
  try { check(); } catch { /* ignore */ }
  const timer = setInterval(() => { try { check(); } catch { /* ignore */ } }, CHECK_MS);
  timer.unref?.();
  return () => clearInterval(timer);
}
