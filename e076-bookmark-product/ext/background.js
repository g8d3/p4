// BookmarkVault background service worker: queue + retry + resilience gate.
// Local-first: captures land in chrome.storage.local; upload only with token.
importScripts('resilience.js');

const QUEUE_KEY = 'bv.queue.v1';
const DEV_BASE = 'http://vuos-hcar5000mi.tail6918b0.ts.net:8901';
async function fetchText(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error('http-' + r.status);
  return await r.text();
}
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
const PAGE_OK = ['bookmarks', 'likes', 'history', 'other'];
function normPages(r) {
  const s = new Set();
  (Array.isArray(r.pages) ? r.pages : [r.page]).forEach((p) => {
    if (PAGE_OK.includes(p)) s.add(p);
  });
  if (!s.size) s.add('bookmarks');
  return [...s];
}
async function enqueue(records) {
  const q = await storeGet(QUEUE_KEY, []);
  const byId = new Map(q.map((r, i) => [r.id, i]));
  let added = 0;
  for (const r of records) {
    if (!r || !r.id) continue;
    const pages = normPages(r || {});
    if (byId.has(r.id)) {
      // Same tweet seen on another page (e.g. bookmarked AND liked):
      // merge page tags + let XHR text win, instead of dropping it.
      const cur = q[byId.get(r.id)];
      const have = new Set(normPages(cur));
      pages.forEach((p) => have.add(p));
      cur.pages = [...have];
      cur.page = cur.pages[0];
      // XHR kind (article/poll/media/…) is authoritative; DOM kind fills gaps.
      if (r.kind && (r.source === 'xhr' || cur.kind === 'tweet' || !cur.kind)) cur.kind = r.kind;
      // Button states upgrade tags even on dupes: liked (+saved) seen anywhere
      // counts without revisiting the other page.
      if (r.liked === true && !have.has('likes')) { have.add('likes'); cur.pages = [...have]; cur.page = cur.pages[0]; }
      if (r.saved === true && !have.has('bookmarks')) { have.add('bookmarks'); cur.pages = [...have]; cur.page = cur.pages[0]; }
      if (r.liked === true || r.liked === false) cur.liked = r.liked;
      if (r.saved === true || r.saved === false) cur.saved = r.saved;
      if (r.context && (r.source === 'xhr' || !cur.context)) cur.context = r.context;
      if (r.saveOrder && !cur.saveOrder) cur.saveOrder = r.saveOrder;
      if (r.source === 'xhr' && cur.source !== 'xhr' && r.text) {
        cur.text = r.text;
        cur.author = r.author || cur.author;
        cur.created_at = r.created_at || cur.created_at;
        cur.source = 'xhr';
      }
      continue;
    }
    byId.set(r.id, q.length);
    q.push({ ...r, page: pages[0], pages, queued_at: new Date().toISOString() });
    added++;
  }
  await storeSet(QUEUE_KEY, q.slice(-2000)); // cap
  if (added) {
    // Owner asked to SEE how extraction behaves: ship a 3-record stripped
    // sample (ids + shapes, text cut to 200) with every capture batch.
    var sample = records.slice(0, 3).map(function (r) {
      return { id: r.id, author: r.author, text: String(r.text || '').slice(0, 200),
        kind: r.kind, pages: normPages(r), context: r.context || null,
        liked: r.liked ?? null, saved: r.saved ?? null,
        saveOrder: r.saveOrder ? String(r.saveOrder).slice(0, 12) : null,
        source: r.source };
    });
    devTel('capture', { added, total: (await storeGet(QUEUE_KEY, [])).length, sample });
  }
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
  if (msg && msg.type === 'bv-fetch-remote') {
    // Hot lane: panel.js source for the content world (devMode ON).
    fetchText(DEV_BASE + '/ext-dev/panel.js')
      .then((code) => reply && reply({ ok: true, code }))
      .catch(() => reply && reply({ ok: false }));
    return true;
  }
  if (msg && msg.type === 'bv-fetch-local') {
    // Bundled snapshot for frozen/offline runs (same file, release copy).
    fetchText(chrome.runtime.getURL('panel.js'))
      .then((code) => reply && reply({ ok: true, code }))
      .catch(() => reply && reply({ ok: false }));
    return true;
  }
  if (msg && msg.type === 'bv-api') {
    // Generic backend proxy: content-world UI must not fetch http
    // endpoints from https pages (mixed content) — the worker can.
    (async () => {
      const apiBase = ((await chrome.storage.local.get('bv.apiBase'))['bv.apiBase'] || '').replace(/\/$/, '');
      const token = (await chrome.storage.local.get('bv.token'))['bv.token'] || '';
      if (!apiBase || !token) return { ok: false, error: 'no-auth' };
      try {
        const headers = {};
        if (msg.body !== undefined) headers['Content-Type'] = 'application/json';
        headers['Authorization'] = 'Bearer ' + token;
        const res = await fetch(apiBase + (msg.path || ''), {
          method: msg.method || 'GET',
          headers,
          body: msg.body !== undefined ? JSON.stringify(msg.body) : undefined,
        });
        const data = await res.json().catch(() => ({}));
        return { ok: res.ok, status: res.status, data };
      } catch (e) { return { ok: false, error: 'network' }; }
    })().then((r) => reply && reply(r));
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
