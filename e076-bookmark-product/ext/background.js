// BookmarkVault background service worker: queue + retry + resilience gate.
// Local-first: captures land in chrome.storage.local; upload only with token.
importScripts('resilience.js');

const QUEUE_KEY = 'bv.queue.v1';
const DEV_BASE = 'http://vuos-hcar5000mi.tail6918b0.ts.net:8901';
async function tuningRefresh() {
  try {
    const on = (await chrome.storage.local.get('bv.devMode'))['bv.devMode'];
    if (!on) return (await chrome.storage.local.get('bv.tuning'))['bv.tuning'] || null;
    const r = await fetch(DEV_BASE + '/ext-dev/tuning.json').catch(() => null);
    if (r && r.ok) {
      const j = await r.json();
      await chrome.storage.local.set({ 'bv.tuning': j });
      return j;
    }
  } catch (e) {}
  return null;
}
async function devTel(kind, payload) {
  try {
    const off = (await chrome.storage.local.get('bv.devTelOff'))['bv.devTelOff'];
    if (off) return;
    await fetch(DEV_BASE + '/api/telemetry', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, src: 'ext', payload }) }).catch(() => {});
  } catch (e) {}
}
const META_KEY = 'bv.meta.v1';
const MAX_BATCH = 50;

async function storeGet(k, dflt) {
  const o = await chrome.storage.local.get(k);
  return o[k] !== undefined ? o[k] : dflt;
}
async function storeSet(k, v) { await chrome.storage.local.set({ [k]: v }); }

const STATUS_KEY = 'bv.status.v1';
async function touchStatus(patch) {
  const s = await storeGet(STATUS_KEY, { sessionAdded: 0 });
  await storeSet(STATUS_KEY, { ...s, ...patch });
}
async function enqueue(records) {
  const q = await storeGet(QUEUE_KEY, []);
  const seen = new Set(q.map((r) => r.id));
  let added = 0;
  for (const r of records) {
    if (!r || !r.id || seen.has(r.id)) continue;
    seen.add(r.id);
    q.push({ ...r, queued_at: new Date().toISOString() });
    added++;
  }
  await storeSet(QUEUE_KEY, q.slice(-2000)); // cap
  if (added) devTel('capture', { added, total: (await storeGet(QUEUE_KEY, [])).length });
  if (added) touchStatus({ lastCaptureAt: new Date().toISOString(),
    sessionAdded: (await storeGet(STATUS_KEY, { sessionAdded: 0 })).sessionAdded + added });
  // Full-history import checkpoint: keep the saved count on the import card.
  try {
    const imp = await storeGet('bv.import.v1', null);
    if (imp && (imp.state === 'running' || imp.wish === 'run')) {
      await storeSet('bv.import.v1', { ...imp, captured: (imp.captured || 0) + added,
        updated_at: new Date().toISOString() });
    }
  } catch (e) {}
  await updateBadge();
  return added;
}

async function updateBadge() {
  try {
    const q = await storeGet(QUEUE_KEY, []);
    await chrome.action.setBadgeText({ text: q.length ? String(Math.min(q.length, 999)) : '' });
  } catch (e) {}
}

async function trySync() {
  const meta = await storeGet(META_KEY, {});
  const q = await storeGet(QUEUE_KEY, []);
  if (!q.length) return { ok: true, synced: 0, reason: 'empty' };
  const token = (await chrome.storage.local.get('bv.token'))['bv.token'] || '';
  const apiBase = (await chrome.storage.local.get('bv.apiBase'))['bv.apiBase'] || '';
  if (!token || !apiBase) return { ok: false, reason: 'no-auth' }; // stay local

  const plan = { queue: q, meta: meta, batchSize: MAX_BATCH };
  const verdict = BVResilience.score(plan);
  await storeSet(META_KEY, { ...meta, lastScore: verdict.score, lastReasons: verdict.reasons });
  if (verdict.action === 'pause') return { ok: false, reason: 'paused', score: verdict.score };
  const batch = q.slice(0, verdict.action === 'slow' ? Math.ceil(MAX_BATCH / 2) : MAX_BATCH);

  try {
    const res = await fetch(apiBase.replace(/\/$/, '') + '/v1/bookmarks/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
      body: JSON.stringify({ tweets: batch }),
    });
    if (res.status === 429) {
      await storeSet(META_KEY, { ...meta, last429: Date.now(), fails: (meta.fails || 0) + 1 });
      return { ok: false, reason: 'rate-limited' };
    }
    if (!res.ok) {
      await storeSet(META_KEY, { ...meta, fails: (meta.fails || 0) + 1 });
      return { ok: false, reason: 'http-' + res.status };
    }
    const ids = new Set(batch.map((r) => r.id));
    await storeSet(QUEUE_KEY, q.filter((r) => !ids.has(r.id)));
    await storeSet(META_KEY, { ...meta, fails: 0, lastSync: new Date().toISOString(), lastScore: verdict.score });
    await updateBadge();
    return { ok: true, synced: batch.length, score: verdict.score };
  } catch (e) {
    await storeSet(META_KEY, { ...meta, fails: (meta.fails || 0) + 1 });
    return { ok: false, reason: 'network' };
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg && msg.type === 'bv-capture') {
    enqueue(msg.records || []).then((added) => reply && reply({ added }));
    return true;
  }
  if (msg && msg.type === 'bv-exec-main' && _sender && _sender.tab && _sender.tab.id != null) {
    try {
      chrome.scripting.executeScript({ target: { tabId: _sender.tab.id }, files: ['page-tap.js'], world: 'MAIN' }).then(() => reply && reply({ ok: true })).catch((e) => reply && reply({ ok: false }));
    } catch (e) { reply && reply({ ok: false }); }
    return true;
  }
  if (msg && msg.type === 'bv-sync-now') {
    trySync().then((r) => reply && reply(r));
    return true;
  }
  if (msg && msg.type === 'bv-import-challenge') {
    storeGet('bv.import.v1', {}).then((imp) =>
      storeSet('bv.import.v1', { ...imp, wish: 'pause', state: 'challenge',
        reason: (msg && msg.reason) || 'X asked us to slow down',
        cooldownUntil: Date.now() + 10 * 60 * 1000,
        updated_at: new Date().toISOString() })
    ).then(() => reply && reply({ ok: true }));
    return true;
  }
  if (msg && msg.type === 'bv-heartbeat') {
    touchStatus({ watching: true, lastSeenPage: msg.page || '', at: new Date().toISOString() })
      .then(() => reply && reply({ ok: true }));
    return true;
  }
  if (msg && msg.type === 'bv-tuning-refresh') {
    tuningRefresh().then((j) => reply && reply({ ok: !!j, v: (j && j.v) || 0 }));
    return true;
  }
  if (msg && msg.type === 'bv-devmode') {
    chrome.storage.local.set({ 'bv.devMode': !!msg.on }).then(() => reply && reply({ ok: true }));
    return true;
  }
  if (msg && msg.type === 'bv-devnote') {
    devTel('devnote', { note: (msg && msg.note) || '?' });
    if (reply) reply({ ok: true });
    return true;
  }
  if (msg && msg.type === 'bv-stats') {
    Promise.all([storeGet(QUEUE_KEY, []), storeGet(META_KEY, {}), storeGet(STATUS_KEY, {})]).then(([q, meta, status]) =>
      reply && reply({ queued: q.length, meta, status })
    );
    return true;
  }
});

chrome.alarms.create('bv-sync', { periodInMinutes: 15 });
chrome.alarms.onAlarm.addListener((a) => { if (a.name === 'bv-sync') trySync(); });
chrome.runtime.onInstalled.addListener((d) => {
  updateBadge();
  try { chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }); } catch (e) {}
  if (d && d.reason === 'install') {
    try { chrome.tabs.create({ url: chrome.runtime.getURL('onboarding.html') }); } catch (e) {}
  }
});
