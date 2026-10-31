/**
 * Auto-discover OpenCode Zen + Zen Go models and merge them into pi.
 *
 * Why: pi.dev's curated catalog lags the live opencode.ai model lists
 * (e.g. gpt-5.3-codex-spark was missing). `pi.dev/api/models/providers/...`
 * only knows what pi.dev publishes, and models.json is static unless something
 * updates it. This extension closes the gap at every pi launch for BOTH zen
 * providers:
 *
 *   1. Fetch https://opencode.ai/zen/v1/models      (provider `opencode`)
 *      Fetch https://opencode.ai/zen/go/v1/models   (provider `opencode-go`)
 *   2. Read pi's curated snapshots (~/.pi/agent/models-store.json, the
 *      pi.dev overlay with full metadata: prices, contexts, vision, compat)
 *   3. Merge: known ids keep curated metadata; unknown ids are templated from the
 *      closest family model (longest common id prefix) with vision/reasoning hints
 *   4. Write ~/.pi/agent/models.json (both provider entries) and
 *      settings.json enabledModels so everything shows in /model
 *
 * Pure Node (global fetch, fs). No pi imports. Safe when offline: on any fetch
 * failure it leaves both files untouched. Writes are atomic and only happen when
 * content actually changed.
 */

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const AGENT_DIR = path.join(os.homedir(), ".pi", "agent");
const MODELS_STORE = path.join(AGENT_DIR, "models-store.json");
const MODELS_JSON = path.join(AGENT_DIR, "models.json");
const SETTINGS_JSON = path.join(AGENT_DIR, "settings.json");

/** provider id -> live models endpoint (OpenCode Zen regular + Zen Go). */
const PROVIDERS = [
  { id: "opencode", liveUrl: "https://opencode.ai/zen/v1" },
  { id: "opencode-go", liveUrl: "https://opencode.ai/zen/go/v1" },
];
const FETCH_TIMEOUT_MS = 6000;
/** Cache of the live id lists. The two HTTPS fetches cost ~340 ms per pi
 * launch; the live catalog does not change that often, so a fresh cache skips
 * them entirely. `sync-opencode-models` ignores the TTL and always refetches. */
const CACHE_JSON = path.join(AGENT_DIR, "opencode-models-cache.json");
const CACHE_TTL_MS = Number(process.env.PI_OPENCODE_SYNC_TTL_MS || 6 * 60 * 60 * 1000);

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return fallback;
  }
}

/** Pretty model id -> display name, e.g. deepseek-v4-flash-vision-exp -> DeepSeek V4 Flash Vision Exp */
function prettyName(id) {
  return id
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function commonPrefixLen(a, b) {
  let i = 0;
  while (i < a.length && i < b.length && a[i] === b[i]) i++;
  return i;
}

/** Find the curated model with the longest common id prefix against `id`. */
function closestFamily(id, models) {
  let best = null;
  let bestLen = 0;
  for (const m of Object.values(models)) {
    const len = commonPrefixLen(id, m.id);
    if (len > bestLen) {
      bestLen = len;
      best = m;
    }
  }
  return bestLen >= 3 ? best : null;
}

const VISION_HINT = /vision|omni|\bvl\b|-vl\b/i;

/** Template a brand-new live id from the closest curated family model. */
function templateModel(id, family) {
  const m = family ? { ...family, id, name: undefined } : { id };
  if (m.name === undefined) m.name = prettyName(id);
  if (VISION_HINT.test(id)) m.input = ["text", "image"];
  if (!m.cost) m.cost = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };
  if (!m.contextWindow) m.contextWindow = 128000;
  if (!m.maxTokens) m.maxTokens = 16384;
  return m;
}

function atomicWrite(file, data) {
  const tmp = file + ".tmp";
  fs.writeFileSync(tmp, data);
  fs.renameSync(tmp, file);
}

async function fetchLiveIds(baseUrl) {
  const res = await fetch(baseUrl + "/models", { signal: AbortSignal.timeout(FETCH_TIMEOUT_MS) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const payload = await res.json();
  return (payload.data || []).map((m) => m.id).filter(Boolean);
}

async function main({ force = false } = {}) {
  const store = readJson(MODELS_STORE, {});
  const modelsCfg = readJson(MODELS_JSON, {});

  // Live id lists: reuse the cached ones while fresh, refetch otherwise.
  const cache = readJson(CACHE_JSON, null);
  const cacheAge = cache && typeof cache.fetchedAt === "number" ? Date.now() - cache.fetchedAt : Infinity;
  const cacheFresh = !force && cacheAge < CACHE_TTL_MS;
  const liveIdsByProvider = {};
  let cacheDirty = false;
  let cacheUsed = [];

  /** @type {Record<string, {api:string, baseUrl:string, models:any[]}>} */
  const nextProviderEntries = {};
  const log = [];
  const scoped = []; // provider/id entries for settings.json enabledModels

  for (const { id: PROVIDER, liveUrl } of PROVIDERS) {
    // 1. Curated base: pi.dev overlay snapshot (full metadata).
    const curatedList = (store[PROVIDER]?.models || [])
      .filter((m) => m && m.id)
      .map((m) => ({ ...m, provider: PROVIDER }));
    const curated = Object.fromEntries(curatedList.map((m) => [m.id, m]));

    // 2. Existing models.json entries (preserve user intent / atomic additions).
    const existingList = (modelsCfg.providers?.[PROVIDER]?.models || [])
      .filter((m) => m && m.id)
      .map((m) => ({ ...m, provider: PROVIDER }));
    const existing = Object.fromEntries(existingList.map((m) => [m.id, m]));

    // 3. Live ids from opencode.ai (or the fresh cache).
    let liveIds;
    const cachedIds = cacheFresh ? cache.ids?.[PROVIDER] : undefined;
    if (Array.isArray(cachedIds)) {
      liveIds = cachedIds;
      cacheUsed.push(`${PROVIDER} (cache ${Math.round(cacheAge / 60000)}m old)`);
    } else {
      try {
        liveIds = await fetchLiveIds(liveUrl);
        liveIdsByProvider[PROVIDER] = liveIds;
        cacheDirty = true;
      } catch (err) {
        console.warn(`[sync-opencode-models] ${PROVIDER}: live fetch failed (${err.message}); keeping current config.`);
        liveIds = Array.isArray(cache?.ids?.[PROVIDER]) ? cache.ids[PROVIDER] : [];
        if (liveIds.length) cacheUsed.push(`${PROVIDER} (stale cache)`);
      }
    }

    // 4. Merge: curated first (metadata wins for known ids), old models.json next,
    //    then live ids that are entirely new -> templated.
    const merged = { ...curated, ...existing };
    const familyPool = { ...curated, ...existing };
    for (const id of liveIds) {
      if (merged[id]) continue;
      merged[id] = templateModel(id, closestFamily(id, familyPool));
    }

    const finalModels = Object.values(merged).map((m) => {
      const { provider: _p, ...rest } = m;
      return rest;
    });
    nextProviderEntries[PROVIDER] = {
      api: "openai-completions",
      baseUrl: liveUrl,
      models: finalModels,
    };
    scoped.push(...[...Object.keys(merged)].sort().map((mid) => `${PROVIDER}/${mid}`));
    log.push(`${PROVIDER}: ${curatedList.length} curated + ${existingList.length} prior + ${liveIds.length} live -> ${finalModels.length}`);
  }

  // 5. models.json: emit complete snapshots for both providers; preserve
  //    unrelated providers the user configured (this extension owns only the
  //    opencode* providers).
  const otherProviders = { ...(modelsCfg.providers ?? {}) };
  for (const { id } of PROVIDERS) delete otherProviders[id];
  const nextModelsJson = {
    providers: {
      ...otherProviders,
      ...nextProviderEntries,
    },
  };

  // 6. settings.json: if explicit picks exist (the model guard's wanted.json),
  //    enable exactly those for the providers we own; other providers'
  //    entries are left alone. This keeps every pi launch converged with the
  //    picks instead of re-enabling the whole catalog behind the user's back.
  //    Without recorded picks, fall back to enabling every discovered id so
  //    everything shows in /model.
  const settings = readJson(SETTINGS_JSON, {});
  const enabled = settings.enabledModels ?? [];
  const owned = new Set(PROVIDERS.map((p) => p.id + "/"));
  const unowned = enabled.filter((pat) => !owned.has(String(pat).slice(0, pat.indexOf("/") + 1)));
  const wanted = readJson(
    path.join(os.homedir(), ".pi-web", "plugin-data", "p4-models", "wanted.json"),
    null
  );
  const picks =
    wanted && Array.isArray(wanted.models) && wanted.models.length
      ? [...new Set(wanted.models)].sort()
      : null;
  const nextEnabled = picks
    ? [...unowned.filter((pat) => !picks.includes(pat)), ...picks]
    : [...unowned, ...scoped.sort()];
  const nextSettings = { ...settings, enabledModels: nextEnabled };

  // 7. Write only when changed, atomically.
  const modelsStr = JSON.stringify(nextModelsJson, null, 2) + "\n";
  const settingsStr = JSON.stringify(nextSettings, null, 2) + "\n";
  let wrote = [];
  if (fs.existsSync(MODELS_JSON) && fs.readFileSync(MODELS_JSON, "utf8") === modelsStr) {
    // unchanged
  } else {
    atomicWrite(MODELS_JSON, modelsStr);
    wrote.push("models.json");
  }
  if (fs.existsSync(SETTINGS_JSON) && fs.readFileSync(SETTINGS_JSON, "utf8") === settingsStr) {
    // unchanged
  } else {
    atomicWrite(SETTINGS_JSON, settingsStr);
    wrote.push("settings.json");
  }

  if (cacheDirty) {
    const ids = { ...(cache?.ids ?? {}), ...liveIdsByProvider };
    try {
      atomicWrite(CACHE_JSON, JSON.stringify({ fetchedAt: Date.now(), ids }, null, 2) + "\n");
    } catch (err) {
      console.warn(`[sync-opencode-models] cache write failed: ${err.message}`);
    }
  }

  console.log(
    `[sync-opencode-models] ${log.join(" | ")} (${wrote.length ? "wrote " + wrote.join(", ") : "no changes"})` +
      (cacheUsed.length ? ` [live ids from ${cacheUsed.join(", ")}]` : "")
  );
}

module.exports = async function (pi) {
  try {
    await main();
  } catch (err) {
    console.warn(`[sync-opencode-models] sync failed: ${err.message}`);
  }

  // On-demand refresh from inside pi without restarting.
  pi.registerCommand("sync-opencode-models", {
    description: "Re-sync OpenCode Zen + Zen Go models from opencode.ai",
    async handler() {
      await main({ force: true });
    },
  });
};
