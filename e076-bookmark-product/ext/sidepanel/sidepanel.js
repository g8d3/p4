// Sidepanel: Saved search reads GET /v1/bookmarks?q=&label= when online
// (server search + label filter), merged with local-only items; falls back
// to chrome.storage.local queue when offline or without API base + token.
// Labels are local-first: always saved on device (bv.labels.v1 / bv.labeldefs.v1),
// mirrored to GET/POST /v1/labels and POST/DELETE /v1/bookmarks/:id/labels when
// an API base + token is configured. Without them, everything stays local.
// Approvals are local-first too (bv.approvals.v1): propose creates a pending
// item, Approve/Reject only flips its status — nothing runs on propose.
(function () {
  'use strict';
  // HTTP-preview fallback: the real extension provides chrome.storage;
  // over plain http (screenshots, reviews) emulate it on localStorage.
  if (typeof chrome === 'undefined' || !chrome.storage) {
    var __bvMem = {};
    try { __bvMem = JSON.parse(localStorage.getItem('bv.preview.v1') || '{}'); } catch (e) { __bvMem = {}; }
    var __bvSave = function () { try { localStorage.setItem('bv.preview.v1', JSON.stringify(__bvMem)); } catch (e) {} };
    var __bvGet = function (k) {
      return new Promise(function (res) {
        var o = {};
        (Array.isArray(k) ? k : [k]).forEach(function (key) { o[key] = __bvMem[key]; });
        res(o);
      });
    };
    var __bvSet = function (o) { return new Promise(function (res) { Object.keys(o).forEach(function (k) { __bvMem[k] = o[k]; }); __bvSave(); res(); }); };
    window.chrome = { storage: { local: { get: __bvGet, set: __bvSet }, onChanged: { addListener: function () {} } }, runtime: { sendMessage: function (m, cb) { if (cb) cb({}); } } };
  }
  var QUEUE_KEY = 'bv.queue.v1';
  var LABELS_KEY = 'bv.labels.v1';
  var LABELDEFS_KEY = 'bv.labeldefs.v1';
  var WEBHOOKS_KEY = 'bv.webhooks.v1';
  var APPROVALS_KEY = 'bv.approvals.v1';
  var activeLabel = '';

  var tabs = Array.prototype.slice.call(document.querySelectorAll('nav.tabs button'));
  var panes = Array.prototype.slice.call(document.querySelectorAll('.pane'));
  function showPane(id, pushHash) {
    tabs.forEach(function (x) { x.setAttribute('aria-selected', x.dataset.pane === id ? 'true' : 'false'); });
    panes.forEach(function (p) { p.classList.toggle('active', p.id === id); });
    // replaceState, not location.hash: no scroll steal, shareable link.
    // + storage: mobile panels reopen fresh on every icon tap (hash lost), storage survives.
    if (pushHash) { try { history.replaceState(null, '', '#' + id.replace(/^pane-/, '')); } catch (e) {} }
    try { chrome.storage.local.set({ 'bv.pane': id }); } catch (e) {}
  }
  tabs.forEach(function (b) {
    b.addEventListener('click', function () { showPane(b.dataset.pane, true); });
  });
  // Deep link: index.html#labels opens the Labels pane on load (for links + screenshots).
  // Storage fallback: mobile panels reopen fresh (hash lost) — last pane wins.
  (function () {
    function apply(id) { if (document.getElementById(id)) showPane(id, false); }
    var h = (location.hash || '').replace('#', '');
    if (h && document.getElementById('pane-' + h)) { apply('pane-' + h); return; }
    try {
      chrome.storage.local.get('bv.pane').then(function (o) {
        if (o && o['bv.pane']) apply(o['bv.pane']);
      });
    } catch (e) {}
  })();

  function getQueue() {
    return chrome.storage.local.get(QUEUE_KEY).then(function (o) { return o[QUEUE_KEY] || []; });
  }
  function getLabelMap() {
    return chrome.storage.local.get(LABELS_KEY).then(function (o) { return o[LABELS_KEY] || {}; });
  }
  function getLabelDefs() {
    return chrome.storage.local.get(LABELDEFS_KEY).then(function (o) { return o[LABELDEFS_KEY] || []; });
  }
  function setLabelMap(m) { return chrome.storage.local.set({ [LABELS_KEY]: m }); }
  function setLabelDefs(d) { return chrome.storage.local.set({ [LABELDEFS_KEY]: d }); }
  function getWebhooks() {
    return chrome.storage.local.get(WEBHOOKS_KEY).then(function (o) { return o[WEBHOOKS_KEY] || []; });
  }
  function setWebhooks(w) { return chrome.storage.local.set({ [WEBHOOKS_KEY]: w }); }
  function getApprovals() {
    return chrome.storage.local.get(APPROVALS_KEY).then(function (o) { return o[APPROVALS_KEY] || []; });
  }
  function setApprovals(a) { return chrome.storage.local.set({ [APPROVALS_KEY]: a }); }
  function getApi() {
    return chrome.storage.local.get(['bv.apiBase', 'bv.token']).then(function (o) {
      return {
        apiBase: ((o['bv.apiBase'] || '').replace(/\/$/, '')),
        token: (o['bv.token'] || '')
      };
    });
  }
  function esc(s) { return String(s || '').replace(/[&<>\"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmtDate(s) {
    if (!s) return '';
    var d = new Date(s);
    if (isNaN(d.getTime())) return String(s).slice(0, 16);
    try { return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); }
    catch (e) { return d.toLocaleString(); }
  }
  // Relevance: newest-first sort key (created_at, then queued/imported, else 0).
  function tsOf(r) {
    var t = Date.parse(r.created_at || r.queued_at || r.imported_at || '');
    return isNaN(t) ? 0 : t;
  }
  function newestFirst(a, b) { return tsOf(b) - tsOf(a); }
  // Dupe signal: normalized text shared by 2+ ids (URLs stripped, case/space folded).
  function normText(r) {
    return String(r.text || '').toLowerCase().replace(/https?:\/\/\S+/g, '')
      .replace(/\s+/g, ' ').trim().slice(0, 160);
  }
  function dupeCounts(items) {
    var n = {};
    items.forEach(function (r) {
      var k = normText(r);
      if (k.length >= 20) n[k] = (n[k] || 0) + 1;
    });
    return n;
  }
  function labelsOf(r, map) {
    var fromRec = Array.isArray(r.labels) ? r.labels : [];
    var fromMap = map[r.id] || [];
    var seen = {};
    return fromRec.concat(fromMap).filter(function (l) {
      if (!l || seen[l]) return false;
      seen[l] = true;
      return true;
    });
  }

  // --- server mirror (best-effort; local always wins on failure) ---
  function serverLabels() {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return null;
      return fetch(a.apiBase + '/v1/labels', {
        headers: { Authorization: 'Bearer ' + a.token }
      }).then(function (res) {
        if (!res.ok) throw new Error('http-' + res.status);
        return res.json();
      }).then(function (p) {
        return (p.labels || []).map(function (l) { return l.name; }).filter(Boolean);
      }).catch(function () { return null; });
    });
  }
  function serverCreate(name) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/labels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({ name: name })
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }
  function serverAttach(id, label) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/bookmarks/' + encodeURIComponent(id) + '/labels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({ label: label })
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }
  function serverDetach(id, label) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/bookmarks/' + encodeURIComponent(id) + '/labels', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({ label: label })
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }

  // --- server search (GET /v1/bookmarks?q=&label=); null = no creds, 'error' = offline ---
  function serverSearch(qstr, label) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return null;
      var url = a.apiBase + '/v1/bookmarks?q=' + encodeURIComponent(qstr || '') +
        '&label=' + encodeURIComponent(label || '');
      return fetch(url, { headers: { Authorization: 'Bearer ' + a.token } })
        .then(function (res) {
          if (!res.ok) throw new Error('http-' + res.status);
          return res.json();
        })
        .then(function (p) {
          return { tweets: p.tweets || [], total: (p.total != null ? p.total : (p.tweets || []).length) };
        })
        .catch(function () { return 'error'; });
    });
  }
  function render(q, map, qstr, serverData) {
    var list = document.getElementById('list');
    qstr = (qstr || '').toLowerCase();
    var items, mode;
    if (serverData && Array.isArray(serverData.tweets)) {
      // Online: server already applied q + label filter. Merge local-only ids not yet synced.
      var seen = {};
      serverData.tweets.forEach(function (r) { seen[r.id] = true; });
      var localOnly = q.filter(function (r) {
        if (seen[r.id]) return false;
        if (activeLabel && labelsOf(r, map).indexOf(activeLabel) < 0) return false;
        if (!qstr) return true;
        return ((r.text || '') + ' ' + (r.author || '')).toLowerCase().indexOf(qstr) >= 0;
      });
      items = serverData.tweets.concat(localOnly).sort(newestFirst).slice(0, 100);
      mode = 'server';
    } else {
      items = q.filter(function (r) {
        if (activeLabel && labelsOf(r, map).indexOf(activeLabel) < 0) return false;
        if (!qstr) return true;
        return ((r.text || '') + ' ' + (r.author || '')).toLowerCase().indexOf(qstr) >= 0;
      }).sort(newestFirst).slice(0, 100);
      mode = (serverData === 'error') ? 'offline' : 'local';
    }
    return getLabelDefs().then(function (defs) {
      var dupes = dupeCounts(items);
      var dupeShown = 0;
      list.innerHTML = items.length ? items.map(function (r) {
        var dk = normText(r);
        var isDupe = dk.length >= 20 && dupes[dk] > 1;
        if (isDupe) dupeShown++;
        var dupeBadge = isDupe
          ? '<span class="dupe" title="Same text saved ' + dupes[dk] + ' times">Possible duplicate \u00d7' + dupes[dk] + '</span>' : '';
        var labs = labelsOf(r, map);
        var chips = labs.map(function (l) {
          return '<span class="chip">' + esc(l) +
            '<button data-act="detach" data-id="' + esc(r.id) + '" data-label="' + esc(l) +
            '" title="Remove label" aria-label="Remove ' + esc(l) + '">×</button></span>';
        }).join('');
        var opts = defs.filter(function (d) { return labs.indexOf(d) < 0; })
          .map(function (d) { return '<option value="' + esc(d) + '">' + esc(d) + '</option>'; })
          .join('');
        var attach = defs.length && opts
          ? '<div class="attach"><select data-attach-for="' + esc(r.id) +
            '" aria-label="Attach label">' + opts +
            '</select><button data-act="attach" data-id="' + esc(r.id) + '">Add</button></div>'
          : '<div class="attach"><span class="hint" style="padding:0">No more labels — create one in the Labels tab.</span></div>';
        var openUrl = 'https://x.com/i/status/' + encodeURIComponent(r.id);
        return '<li><div class="txt" title="' + esc((r.text || '').slice(0, 500)) + '">' + esc((r.text || '').slice(0, 220)) + '</div>' +
          '<div class="meta"><span>@' + esc(r.author || '?') + '</span><span>' + esc(fmtDate(r.created_at)) + '</span>' +
          '<span class="src">' + esc(r.source || '?') + '</span>' +
          '<a class="open" href="' + openUrl + '" target="_blank" rel="noopener">Open</a>' + dupeBadge + '</div>' +
          (chips ? '<div class="chips">' + chips + '</div>' : '') + attach + '</li>';
      }).join('') : (qstr || activeLabel
        ? '<li>No matches for this search. <button data-act="clear">Clear search</button></li>'
        : '<li>No saved bookmarks yet. Browse your X bookmarks and they appear here.</li>');
      var st = document.getElementById('status');
      var orderNote = items.length > 1 ? ' · newest first' : '';
      var dupeNote = dupeShown ? ' · ' + dupeShown + ' possible duplicate' + (dupeShown > 1 ? 's' : '') : '';
      if (mode === 'server') {
        st.textContent = serverData.total + ' from server' +
          (activeLabel ? ' · label: ' + activeLabel : '') +
          (qstr ? ' · "' + qstr + '"' : '') +
          ' · ' + items.length + ' shown' + orderNote + dupeNote;
      } else if (mode === 'offline') {
        st.textContent = q.length + ' saved locally (server unreachable, showing local results)' +
          (activeLabel ? ' · label: ' + activeLabel : '') +
          (qstr ? ' · ' + items.length + ' match' : '') + orderNote + dupeNote;
      } else {
        st.textContent = q.length + ' saved locally' +
          (activeLabel ? ' · label: ' + activeLabel : '') +
          (qstr ? ' · ' + items.length + ' match' : '') + orderNote + dupeNote;
      }
    });
  }

  // --- outbound webhooks (local-first; POST /v1/webhooks/bookmarks + GET list) ---
  function serverWebhookList() {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return null;
      return fetch(a.apiBase + '/v1/webhooks/bookmarks', {
        headers: { Authorization: 'Bearer ' + a.token }
      }).then(function (res) {
        if (!res.ok) throw new Error('http-' + res.status);
        return res.json();
      }).then(function (p) {
        return (p.webhooks || []).map(function (w) {
          return typeof w === 'string' ? w : w.url;
        }).filter(Boolean);
      }).catch(function () { return 'error'; });
    });
  }
  function serverWebhookAdd(url) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/webhooks/bookmarks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({ url: url })
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }
  function validWebhookUrl(s) {
    s = String(s || '').trim();
    return (/^https:\/\/\S+/.test(s) || /^http:\/\/localhost(:\d+)?\/\S*/.test(s) ||
      /^http:\/\/127\.0\.0\.1(:\d+)?\/\S*/.test(s)) && s.length <= 500;
  }
  function renderWebhooksPane(local, serverState) {
    var ul = document.getElementById('whList');
    var status = document.getElementById('whStatus');
    if (!ul || !status) return;
    var seen = {};
    var urls = (local || []).map(function (w) { return typeof w === 'string' ? w : w.url; })
      .filter(Boolean).filter(function (u) {
        if (seen[u]) return false;
        seen[u] = true;
        return true;
      });
    ul.innerHTML = urls.length ? urls.map(function (u) {
      return '<li>' + esc(u) + '</li>';
    }).join('') : '<li>No webhook URLs yet. Add one above.</li>';
    if (serverState === null) {
      status.textContent = urls.length
        ? urls.length + ' URL(s), saved on this device only (no API base + token in Sync tab).'
        : 'Local-only (no API base + token in Sync tab).';
    } else if (serverState === 'ok') {
      status.textContent = urls.length
        ? urls.length + ' URL(s), registered with server.'
        : 'No webhook URLs yet. Add one above.';
    } else {
      status.textContent = urls.length
        ? urls.length + ' URL(s), saved locally (server unreachable, will retry).'
        : 'Server unreachable. URLs you add stay on this device and retry later.';
    }
  }
  function refreshWebhooks() {
    return getWebhooks().then(function (local) {
      return serverWebhookList().then(function (names) {
        if (Array.isArray(names)) {
          var seen = {};
          var merged = local.slice();
          merged.forEach(function (w) { seen[typeof w === 'string' ? w : w.url] = true; });
          var changed = false;
          names.forEach(function (u) {
            if (!seen[u]) { merged.push({ url: u, created_at: '' }); changed = true; }
          });
          if (changed) setWebhooks(merged);
          renderWebhooksPane(changed ? merged : local, 'ok');
        } else {
          renderWebhooksPane(local, names === null ? null : 'error');
        }
      });
    });
  }
  function renderLabelsPane(defs, map, serverState) {
    var ul = document.getElementById('labList');
    var status = document.getElementById('labStatus');
    var counts = {};
    Object.keys(map).forEach(function (id) {
      (map[id] || []).forEach(function (l) { counts[l] = (counts[l] || 0) + 1; });
    });
    ul.innerHTML = defs.length ? defs.map(function (d) {
      var c = counts[d] || 0;
      var on = activeLabel === d ? ' · showing' : '';
      return '<li><span class="nm">' + esc(d) + '</span>' +
        '<span class="ct">' + c + ' saved' + esc(on) + '</span>' +
        '<button data-act="filter" data-label="' + esc(d) + '">' +
        (activeLabel === d ? 'Clear' : 'Show') + '</button></li>';
    }).join('') : '<li>No labels yet. Create one above.</li>';
    status.textContent = serverState === null
      ? 'Local-only (no API base + token in Sync tab).'
      : serverState === 'ok'
        ? defs.length + ' label(s), synced with server.'
        : defs.length + ' label(s), saved locally (server unreachable, will retry).';
    // filter dropdown in Saved pane
    var sel = document.getElementById('labelFilter');
    var cur = activeLabel;
    sel.innerHTML = '<option value="">All labels</option>' + defs.map(function (d) {
      return '<option value="' + esc(d) + '"' + (d === cur ? ' selected' : '') + '>' + esc(d) + '</option>';
    }).join('');
  }

  // --- approvals: propose -> approve/reject (local-first; server mirror) ---
  // Risky steps (e.g. resuming a paused sync) wait as pending until the
  // user taps Approve. Nothing runs on propose; decide only flips status.
  function serverApprovalList() {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return null;
      return fetch(a.apiBase + '/v1/approvals', {
        headers: { Authorization: 'Bearer ' + a.token }
      }).then(function (res) {
        if (!res.ok) throw new Error('http-' + res.status);
        return res.json();
      }).then(function (p) {
        return (p.approvals || []).filter(Boolean);
      }).catch(function () { return 'error'; });
    });
  }
  function serverPropose(title) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/approvals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({ kind: 'general', title: title })
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }
  function serverDecide(id, verdict) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/approvals/' + encodeURIComponent(id) + '/' + verdict, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({})
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }
  function renderApprovalsPane(local, serverState) {
    var ul = document.getElementById('apList');
    var status = document.getElementById('apStatus');
    if (!ul || !status) return;
    var items = (local || []).slice(-50).reverse();
    ul.innerHTML = items.length ? items.map(function (p) {
      var st = p.status || 'pending';
      var actions = st === 'pending'
        ? '<div class="row2"><button data-act="ap-approve" data-id="' + esc(p.id) + '">Approve</button>' +
          '<button data-act="ap-reject" data-id="' + esc(p.id) + '">Reject</button></div>'
        : '';
      return '<li><span class="t">' + esc(p.title || '(untitled)') + '</span>' +
        '<span class="st">' + esc(st) + '</span>' + actions + '</li>';
    }).join('') : '<li>No proposed actions. Propose one above to try the flow.</li>';
    var pending = (local || []).filter(function (p) { return (p.status || 'pending') === 'pending'; }).length;
    if (serverState === null) {
      status.textContent = pending
        ? pending + ' waiting, saved on this device only (no API base + token in Sync tab).'
        : 'Local-only (no API base + token in Sync tab).';
    } else if (serverState === 'ok') {
      status.textContent = pending
        ? pending + ' waiting your decision, synced with server.'
        : 'Nothing waiting. Propose an action to try the flow.';
    } else {
      status.textContent = pending
        ? pending + ' waiting, saved locally (server unreachable, will retry).'
        : 'Server unreachable. Proposals you add stay on this device and retry later.';
    }
  }
  function refreshApprovals() {
    return getApprovals().then(function (local) {
      return serverApprovalList().then(function (names) {
        if (Array.isArray(names)) {
          var seen = {};
          local.forEach(function (p) { seen[String(p.id)] = true; });
          var merged = local.slice();
          var changed = false;
          names.forEach(function (s) {
            if (!seen[String(s.id)]) { merged.push(s); changed = true; }
          });
          if (changed) setApprovals(merged);
          renderApprovalsPane(changed ? merged : local, 'ok');
        } else {
          renderApprovalsPane(local, names === null ? null : 'error');
        }
      });
    });
  }

  document.getElementById('whAdd').addEventListener('click', function () {
    var inp = document.getElementById('whUrl');
    var url = String(inp.value || '').trim();
    if (!validWebhookUrl(url)) {
      var st0 = document.getElementById('whStatus');
      if (st0) st0.textContent = 'Enter an https:// URL (http://localhost allowed for testing).';
      inp.focus();
      return;
    }
    getWebhooks().then(function (local) {
      var urls = local.map(function (w) { return typeof w === 'string' ? w : w.url; });
      if (urls.indexOf(url) < 0) {
        local.push({ url: url, created_at: new Date().toISOString() });
        return setWebhooks(local);
      }
      return local;
    }).then(function () {
      inp.value = '';
      inp.focus();
      return serverWebhookAdd(url).then(refreshWebhooks);
    });
  });
  function refresh() {
    var qstr = document.getElementById('search').value;
    return Promise.all([getQueue(), getLabelMap(), getLabelDefs(), serverSearch(qstr, activeLabel)]).then(function (parts) {
      var q = parts[0], map = parts[1], defs = parts[2], serverData = parts[3];
      return render(q, map, qstr, serverData).then(function () {
        chrome.runtime.sendMessage({ type: 'bv-stats' }, function (s) {
          var h = document.getElementById('health');
          if (!h) return;
          if (!s) { h.textContent = ''; return; }
          // HTTP preview has no background worker: fall back to the local queue count.
          if (typeof s.queued !== 'number') { h.textContent = 'Queue ' + q.length + ' · never synced'; return; }
          var m = s.meta || {}, st = s.status || {};
          var live = st.watching ? 'watching bookmarks now' : 'open x.com/i/bookmarks to capture';
          var sess = st.sessionAdded ? ' · +' + st.sessionAdded + ' this session' : '';
          var last = st.lastCaptureAt ? ' · last ' + st.lastCaptureAt.slice(11, 16) : '';
          h.textContent = live + sess + last + ' · Queue ' + s.queued +
            (m.lastSync ? ' · last sync ' + m.lastSync : ' · never synced') +
            (typeof m.lastScore === 'number' ? ' · risk ' + m.lastScore : '') +
            (m.lastReasons && m.lastReasons.length ? ' (' + m.lastReasons.join('; ') + ')' : '');
        });
      }).then(refreshWebhooks).then(function () {
        return serverLabels().then(function (names) {
          if (names) {
            var merged = defs.slice();
            names.forEach(function (n) { if (merged.indexOf(n) < 0) merged.push(n); });
            merged.sort();
            if (merged.join() !== defs.join()) {
              defs = merged;
              setLabelDefs(defs);
            }
            renderLabelsPane(defs, map, 'ok');
          } else {
            renderLabelsPane(defs, map, null);
          }
        });
      }).then(refreshApprovals);
    });
  }

  function cleanName(s) { return String(s || '').trim().replace(/\s+/g, ' ').slice(0, 40); }

  document.getElementById('labCreate').addEventListener('click', function () {
    var inp = document.getElementById('labName');
    var name = cleanName(inp.value);
    if (!name) { inp.focus(); return; }
    getLabelDefs().then(function (defs) {
      if (defs.indexOf(name) < 0) {
        defs.push(name);
        defs.sort();
        return setLabelDefs(defs).then(function () { return defs; });
      }
      return defs;
    }).then(function () {
      inp.value = '';
      inp.focus();
      return serverCreate(name).then(refresh);
    });
  });

  document.getElementById('apAdd').addEventListener('click', function () {
    var inp = document.getElementById('apTitle');
    var title = String(inp.value || '').trim().replace(/\s+/g, ' ').slice(0, 120);
    if (!title) { inp.focus(); return; }
    var item = { id: 'local-' + Date.now(), kind: 'general', title: title,
                 status: 'pending', created_at: new Date().toISOString() };
    getApprovals().then(function (local) {
      local.push(item);
      return setApprovals(local.slice(-200));
    }).then(function () {
      inp.value = '';
      inp.focus();
      return serverPropose(title).then(refreshApprovals);
    });
  });

  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.dataset || !t.dataset.act) return;
    var id = t.dataset.id, label = t.dataset.label;
    if (t.dataset.act === 'clear') {
      activeLabel = '';
      var si = document.getElementById('search');
      if (si) si.value = '';
      var lf = document.getElementById('labelFilter');
      if (lf) lf.value = '';
      refresh();
    } else if (t.dataset.act === 'detach') {
      getLabelMap().then(function (map) {
        map[id] = (map[id] || []).filter(function (l) { return l !== label; });
        if (!map[id].length) delete map[id];
        return setLabelMap(map);
      }).then(function () { return serverDetach(id, label); }).then(refresh);
    } else if (t.dataset.act === 'attach') {
      var sel = document.querySelector('select[data-attach-for="' + CSS.escape(id) + '"]');
      var name = sel ? cleanName(sel.value) : '';
      if (!name) return;
      Promise.all([getLabelMap(), getLabelDefs()]).then(function (parts) {
        var map = parts[0], defs = parts[1];
        if (defs.indexOf(name) < 0) { defs.push(name); defs.sort(); }
        var cur = map[id] || [];
        if (cur.indexOf(name) < 0) cur.push(name);
        map[id] = cur;
        return Promise.all([setLabelMap(map), setLabelDefs(defs)]);
      }).then(function () { return serverAttach(id, name); }).then(refresh);
    } else if (t.dataset.act === 'ap-approve' || t.dataset.act === 'ap-reject') {
      var verdict = t.dataset.act === 'ap-approve' ? 'approve' : 'reject';
      var decided = verdict === 'approve' ? 'approved' : 'rejected';
      getApprovals().then(function (local) {
        var hit = null;
        local.forEach(function (p) {
          if (String(p.id) === String(id) && (p.status || 'pending') === 'pending') {
            p.status = decided;
            p.decided_at = new Date().toISOString();
            hit = p;
          }
        });
        return setApprovals(local).then(function () { return hit; });
      }).then(function (hit) {
        // Server mirror only for server-issued numeric ids; local-only stays local.
        if (hit && typeof hit.id === 'number') return serverDecide(hit.id, verdict);
        return false;
      }).then(refreshApprovals);
    } else if (t.dataset.act === 'filter') {
      activeLabel = (activeLabel === label) ? '' : label;
      // jump to Saved pane so the result is visible (no scroll steal: tab switch only)
      showPane('pane-saved', true);
      refresh();
    }
  });

  document.getElementById('clearSearch').addEventListener('click', function () {
    activeLabel = '';
    document.getElementById('search').value = '';
    document.getElementById('labelFilter').value = '';
    refresh(); // user-initiated: no scroll steal, list re-renders in place
  });
  document.getElementById('labelFilter').addEventListener('change', function (ev) {
    activeLabel = ev.target.value || '';
    refresh();
  });

  var searchTimer = null;
  document.getElementById('search').addEventListener('input', function () {
    // Debounced so each keystroke does not hammer GET /v1/bookmarks; no scroll steal.
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(refresh, 250);
  });
  chrome.storage.onChanged.addListener(function (chg) {
    if (chg[QUEUE_KEY] || chg[LABELS_KEY] || chg[LABELDEFS_KEY] || chg[WEBHOOKS_KEY] || chg[APPROVALS_KEY]) refresh();
    if (chg[IMPORT_KEY]) renderImport(chg[IMPORT_KEY].newValue); // progress never moves scroll
  });

  // --- Full-history import: user-started, checkpoint/resume, pause on challenge ---
  var IMPORT_KEY = 'bv.import.v1';
  function getImport() {
    return chrome.storage.local.get(IMPORT_KEY).then(function (o) { return o[IMPORT_KEY] || null; });
  }
  function setImport(patch) {
    return getImport().then(function (cur) {
      var nxt = Object.assign({}, cur || {}, patch, { updated_at: new Date().toISOString() });
      var obj = {}; obj[IMPORT_KEY] = nxt;
      return chrome.storage.local.set(obj).then(function () { renderImport(nxt); return nxt; });
    });
  }
  function fmtClock(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    try { return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); }
    catch (e) { return d.toLocaleString(); }
  }
  function renderImport(st) {
    var el = document.getElementById('impStatus');
    var bs = document.getElementById('impStart');
    if (!el) return;
    if (!st || (!st.wish && !st.state)) {
      el.textContent = 'Not started yet. Your place is kept on this device.';
      if (bs) bs.textContent = 'Start import';
      return;
    }
    var done = st.state === 'done';
    var chal = st.state === 'challenge';
    var running = st.wish === 'run' && !done && !chal;
    var n = st.scrolls || 0, c = st.captured || 0;
    var base = done ? 'Finished. ' : chal ? 'Paused — ' + (st.reason || 'X asked us to slow down') + '. ' :
      running ? 'Importing slowly… ' : 'Paused. Your place is kept. ';
    var prog = n + ' scrolled · ' + c + ' saved here';
    var when = st.updated_at ? ' · ' + fmtClock(st.updated_at) : '';
    var tip = chal ? ' Tap Start import to try again.' :
      done ? ' Tap Start import to run it again.' :
      running ? ' Keep this tab open. You can Pause anytime.' : ' Tap Start import to pick up where you left off.';
    el.textContent = base + prog + when + '.' + tip;
    if (bs) bs.textContent = done ? 'Run again' : (running ? 'Running…' : (n ? 'Resume import' : 'Start import'));
  }
  function refreshImport() { return getImport().then(renderImport); }
  var __impStart = document.getElementById('impStart');
  if (__impStart) __impStart.addEventListener('click', function () {
    getImport().then(function (cur) {
      var fresh = (!cur || cur.state === 'done')
        ? { wish: 'run', state: 'running', scrolls: 0, captured: 0, checkpointY: 0, checkpointId: '', reason: '', cooldownUntil: 0 }
        : { wish: 'run', state: 'running', reason: '', cooldownUntil: 0 };
      return setImport(fresh);
    });
  });
  var __impPause = document.getElementById('impPause');
  if (__impPause) __impPause.addEventListener('click', function () {
    setImport({ wish: 'pause', state: 'paused' });
  });

  function planLine(p) {
    if (!p) return 'Plan: unknown (offline or no token). Staying local-only.';
    var d = p.plan_detail || {};
    var label = d.label || p.plan || 'Free';
    var extra = p.mode === 'test' ? ' · test mode' : '';
    var upd = p.updated_at ? ' · updated ' + p.updated_at : '';
    return 'Plan: ' + label + extra + upd;
  }

  function fetchPlan() {
    var el = document.getElementById('plan');
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) {
        el.textContent = 'Plan: Free (local-only, no account connected).';
        return null;
      }
      el.textContent = 'Plan: checking…';
      return fetch(a.apiBase + '/v1/billing/me', {
        headers: { Authorization: 'Bearer ' + a.token }
      }).then(function (res) {
        if (!res.ok) throw new Error('http-' + res.status);
        return res.json();
      }).then(function (p) {
        try { chrome.storage.local.set({ 'bv.plan': p.plan || 'free' }); } catch (e) {}
        el.textContent = planLine(p);
        return p;
      }).catch(function () {
        el.textContent = 'Plan: unknown (could not reach billing). Staying local-only.';
        return null;
      });
    });
  }

  document.getElementById('save').addEventListener('click', function () {
    var apiBase = document.getElementById('apiBase').value.trim();
    var token = document.getElementById('token').value.trim();
    chrome.storage.local.set({ 'bv.apiBase': apiBase, 'bv.token': token }).then(function () {
      document.getElementById('status').textContent = apiBase && token ? 'Settings saved.' : 'Cleared — staying local-only.';
      fetchPlan();
      refresh();
    });
  });
  document.getElementById('planBtn').addEventListener('click', fetchPlan);
  chrome.storage.local.get('bv.devMode').then(function (o) {
    document.getElementById('devMode').checked = !!o['bv.devMode'];
  });
  document.getElementById('devMode').addEventListener('change', function (e) {
    chrome.runtime.sendMessage({ type: 'bv-devmode', on: e.target.checked }, function () {
      document.getElementById('tuneHint').textContent = e.target.checked
        ? 'Dev mode ON: tuning loads from server. Tap Refresh tuning, then scroll.'
        : 'Off = store build (frozen).';
    });
  });
  document.getElementById('tuneBtn').addEventListener('click', function () {
    document.getElementById('tuneHint').textContent = 'Fetching…';
    chrome.runtime.sendMessage({ type: 'bv-tuning-refresh' }, function (r) {
      document.getElementById('tuneHint').textContent = r && r.ok
        ? 'Tuning v' + r.v + ' applied. Scroll to feel it.'
        : 'Server unreachable — frozen tuning stays.';
    });
  });
  document.getElementById('sync').addEventListener('click', function () {
    document.getElementById('status').textContent = 'Syncing…';
    chrome.runtime.sendMessage({ type: 'bv-sync-now' }, function (r) {
      document.getElementById('status').textContent = r && r.ok
        ? 'Synced ' + (r.synced || 0) + ' bookmark(s).'
        : 'Still local (' + ((r && r.reason) || 'no connection') + '). Nothing lost.';
      refresh();
    });
  });
  document.getElementById('dl').addEventListener('click', function () {
    Promise.all([getQueue(), getLabelMap()]).then(function (parts) {
      var q = parts[0].map(function (r) {
        return Object.assign({}, r, { labels: labelsOf(r, parts[1]) });
      });
      var blob = new Blob([JSON.stringify(q, null, 2)], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'bookmarkvault-export.json';
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 5000);
    });
  });

  chrome.storage.local.get(['bv.apiBase']).then(function (o) {
    if (o['bv.apiBase']) document.getElementById('apiBase').value = o['bv.apiBase'];
  });
  refresh();
  refreshImport();
  fetchPlan();
})();
