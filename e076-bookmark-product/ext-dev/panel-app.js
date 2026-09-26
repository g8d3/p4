  function mountPanel(SH) {
    var fetch = bgFetch;

  'use strict';
  var QUEUE_KEY = 'bv.queue.v1';
  var LABELS_KEY = 'bv.labels.v1';
  var LABELDEFS_KEY = 'bv.labeldefs.v1';
  var WEBHOOKS_KEY = 'bv.webhooks.v1';
  var APPROVALS_KEY = 'bv.approvals.v1';
  var activeLabel = '';
  var activeType = ''; // '' | 'bookmarks' | 'likes' | 'both'
  var activeLoc = ''; // '' | 'device' | 'server'
  var verifyOn = false; // save-order verification overlay (Saved pane setting)

  var tabs = Array.prototype.slice.call(SH.querySelectorAll('nav.tabs button'));
  var panes = Array.prototype.slice.call(SH.querySelectorAll('.pane'));
  function showPane(id, pushHash) {
    tabs.forEach(function (x) { x.setAttribute('aria-selected', x.dataset.pane === id ? 'true' : 'false'); });
    panes.forEach(function (p) { p.classList.toggle('active', p.id === id); });
    // storage only in-page: never touch the page URL.
    // + storage: mobile panels reopen fresh on every icon tap (hash lost), storage survives.
    if (pushHash) { try { void 0(null, '', '#' + id.replace(/^pane-/, '')); } catch (e) {} }
    try { chrome.storage.local.set({ 'bv.pane': id }); } catch (e) {}
  }
  tabs.forEach(function (b) {
    b.addEventListener('click', function () { showPane(b.dataset.pane, false); });
  });
  try {
    chrome.storage.local.get('bv.pane').then(function (o) {
      if (o && o['bv.pane'] && SH.getElementById(o['bv.pane'])) showPane(o['bv.pane'], false);
    });
  } catch (e) {}

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
  var DEFAULT_BASE = 'http://vuos-hcar5000mi.tail6918b0.ts.net:8899';
  var OPS_BASE = 'http://vuos-hcar5000mi.tail6918b0.ts.net:8901'; // serves ext/manifest.json (update check)
  function getApi() {
    return chrome.storage.local.get(['bv.apiBase', 'bv.token']).then(function (o) {
      var base = (o['bv.apiBase'] || '').replace(/\/$/, '') || DEFAULT_BASE;
      var tok = o['bv.token'] || '';
      if (!tok) {
        // zero-config owner build: create a local random token once (stub accepts any)
        tok = 'local-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
        try { chrome.storage.local.set({ 'bv.token': tok, 'bv.apiBase': base }); } catch (e) {}
      }
      return { apiBase: base, token: tok };
    });
  }
  function esc(s) { return String(s || '').replace(/[&<>\"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmtBuild(iso) {
    // Stored UTC, shown in the viewer's own timezone (owner asked).
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso || '?');
      return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) { return String(iso || '?'); }
  }
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
  function pagesOf(r) {
    if (r && Array.isArray(r.pages) && r.pages.length) return r.pages;
    return [(r && r.page) || 'bookmarks'];
  }
  function typeMatch(r) {
    if (!activeType) return true;
    var st = statusOf(r);
    if (activeType === 'both') return st === 'both';
    if (activeType === 'likes') return st === 'liked' || st === 'both';
    if (activeType === 'bookmarks') return st === 'saved' || st === 'both';
    return pagesOf(r).indexOf(activeType) >= 0;
  }
  // Owner's two levels: liked (good to know) vs both liked+saved (important).
  // Quoted/thread context never counts as saved; DOM 'seen' records resolve
  // through observed button states, else stay 'seen'.
  function statusOf(r) {
    if (r && r.context === 'quoted') return 'quoted';
    var p = pagesOf(r);
    var liked = (r && r.liked === true) || (r && r.liked !== false && p.indexOf('likes') >= 0);
    var saved = (r && r.saved === true) || (r && r.saved !== false && p.indexOf('bookmarks') >= 0);
    if (liked && saved) return 'both';
    if (liked) return 'liked';
    if (saved) return 'saved';
    return 'seen';
  }
  var ST_LABEL = { both: 'liked + bookmarked', liked: 'liked', saved: 'bookmarked', seen: 'seen', quoted: 'quoted' };
  // DOM builders (no HTML strings): structure lives in panel.html <template>,
  // text goes through textContent (auto-escaped).
  function mk(tag, cls, text) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    return el;
  }
  function cloneTpl(id) {
    var t = SH.getElementById(id);
    var n = t && t.content && t.content.firstElementChild;
    return n ? n.cloneNode(true) : null;
  }
  function statusEl(r) {
    var st = statusOf(r);
    return mk('span', 'st st-' + st, ST_LABEL[st]);
  }
  function pageBadges(r) {
    return pagesOf(r).map(function (p) {
      return '<span class="pg pg-' + esc(p) + '">' + esc(p) + '</span>';
    }).join('');
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
        '&label=' + encodeURIComponent(label || '') +
        '&page=' + encodeURIComponent(activeType || '');
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
    var list = SH.getElementById('list');
    qstr = (qstr || '').toLowerCase();
    var items, mode, all, syncedIds = {}, pendingCount = 0;
    function locMatch(r) {
      if (!activeLoc) return true;
      var onServer = (mode === 'server') && !!syncedIds[r.id];
      return activeLoc === 'server' ? onServer : !onServer;
    }
    if (serverData && Array.isArray(serverData.tweets)) {
      // Online: server already applied q + label + type filter. Merge local-only ids not yet synced.
      var seen = {};
      serverData.tweets.forEach(function (r) { seen[r.id] = true; syncedIds[r.id] = true; });
      var localOnly = q.filter(function (r) {
        if (seen[r.id]) return false;
        if (!locMatch(r)) return false;
        if (!typeMatch(r)) return false;
        if (activeLabel && labelsOf(r, map).indexOf(activeLabel) < 0) return false;
        if (!qstr) return true;
        return ((r.text || '') + ' ' + (r.author || '')).toLowerCase().indexOf(qstr) >= 0;
      });
      pendingCount = localOnly.length;
      all = serverData.tweets.filter(function (r) { return typeMatch(r) && locMatch(r); })
        .concat(localOnly).sort(newestFirst);
      items = all.slice(0, 100);
      mode = 'server';
    } else {
      all = q.filter(function (r) {
        if (!locMatch(r)) return false;
        if (!typeMatch(r)) return false;
        if (activeLabel && labelsOf(r, map).indexOf(activeLabel) < 0) return false;
        if (!qstr) return true;
        return ((r.text || '') + ' ' + (r.author || '')).toLowerCase().indexOf(qstr) >= 0;
      }).sort(newestFirst);
      pendingCount = all.length;
      items = all.slice(0, 100);
      mode = (serverData === 'error') ? 'offline' : 'local';
    }
    function syncEl(r) {
      if (mode !== 'server') return mk('span', 'syncpend', 'this device');
      return syncedIds[r.id] ? mk('span', 'syncok', 'on server') : mk('span', 'syncpend', 'upload pending');
    }
    var nLiked = 0, nSaved = 0, nBoth = 0, nQuoted = 0, nSeen = 0;
    all.forEach(function (r) {
      var st = statusOf(r);
      if (st === 'liked') nLiked++;
      else if (st === 'saved') nSaved++;
      else if (st === 'both') nBoth++;
      else if (st === 'quoted') nQuoted++;
      else nSeen++;
    });
    var typeLine = nBoth + ' liked+bookmarked · ' + nLiked + ' liked · ' + nSaved + ' bookmarked' +
      (nQuoted ? ' · ' + nQuoted + ' quoted' : '') + (nSeen ? ' · ' + nSeen + ' seen' : '');
    // Save-order rank from X sortIndex (larger = more recent bookmark; X sends
    // no bookmark creation date, so this ordering is the sync check).
    function ordVal(r) { return String((r && r.saveOrder) || ''); }
    var ranked = all.filter(function (r) { return ordVal(r); }).sort(function (a, b) {
      var x = ordVal(a), y = ordVal(b);
      if (x.length !== y.length) return y.length - x.length;
      return x < y ? 1 : (x > y ? -1 : 0);
    });
    var saveRank = {};
    ranked.forEach(function (r, i) { if (!saveRank[r.id]) saveRank[r.id] = i + 1; });
    var newestSaved = ranked[0] || null, oldestSaved = ranked[ranked.length - 1] || null;

    return getLabelDefs().then(function (defs) {
      var dupes = dupeCounts(items);
      var dupeShown = 0;
      function buildItem(r) {
        var li = cloneTpl('t-item');
        var dk = normText(r);
        var isDupe = dk.length >= 20 && dupes[dk] > 1;
        if (isDupe) dupeShown++;
        li.dataset.tid = r.id;
        li.querySelector('.txt').textContent = String(r.text || '');
        var more = li.querySelector('.morebtn');
        if (String(r.text || '').length > 220) { more.hidden = false; more.dataset.id = r.id; }
        else { more.remove(); }
        var metas = li.querySelectorAll('.meta');
        metas[0].querySelector('.ma').textContent = '@' + (r.author || '?');
        metas[0].querySelector('.md').textContent = fmtDate(r.created_at);
        metas[0].querySelector('.open').href = 'https://x.com/i/status/' + encodeURIComponent(r.id);
        if (isDupe) {
          var db = mk('span', 'dupe', 'Possible duplicate \u00d7' + dupes[dk]);
          db.title = 'Same text saved ' + dupes[dk] + ' times';
          metas[0].appendChild(db);
        }
        var m2 = metas[1];
        m2.appendChild(statusEl(r));
        var kind = (r && r.kind && r.kind !== 'tweet') ? r.kind : '';
        if (kind) m2.appendChild(mk('span', 'kind', kind));
        if (verifyOn && saveRank[r.id]) m2.appendChild(mk('span', 'ord', 'saved #' + saveRank[r.id]));
        m2.appendChild(syncEl(r));
        var labs = labelsOf(r, map);
        var chipsBox = li.querySelector('.chips');
        if (labs.length) {
          chipsBox.hidden = false;
          labs.forEach(function (l) {
            var chip = mk('span', 'chip', l);
            var x = mk('button', null, '\u00d7');
            x.dataset.act = 'detach'; x.dataset.id = r.id; x.dataset.label = l;
            x.title = 'Remove label'; x.setAttribute('aria-label', 'Remove ' + l);
            chip.appendChild(x);
            chipsBox.appendChild(chip);
          });
        } else { chipsBox.remove(); }
        var box = li.querySelector('.attach');
        var opts = defs.filter(function (d) { return labs.indexOf(d) < 0; });
        if (defs.length && opts.length) {
          box.hidden = false;
          var sel = document.createElement('select');
          sel.dataset.attachFor = r.id;
          sel.setAttribute('aria-label', 'Attach label');
          opts.forEach(function (d) {
            var o = document.createElement('option');
            o.value = d; o.textContent = d;
            sel.appendChild(o);
          });
          var add = mk('button', null, 'Add');
          add.dataset.act = 'attach'; add.dataset.id = r.id;
          box.appendChild(sel); box.appendChild(add);
        } else { box.remove(); }
        return li;
      }
      list.textContent = '';
      if (items.length) {
        items.forEach(function (r) { list.appendChild(buildItem(r)); });
      } else {
        var empty = mk('li', null, (qstr || activeLabel)
          ? 'No matches for this search. '
          : 'No saved bookmarks yet. Browse your X bookmarks and they appear here.');
        if (qstr || activeLabel) {
          var cb = mk('button', null, 'Clear search');
          cb.dataset.act = 'clear';
          empty.appendChild(cb);
        }
        list.appendChild(empty);
      }
      var st = SH.getElementById('status');
      var orderNote = items.length > 1 ? ' · newest first' : '';
      var dupeNote = dupeShown ? ' · ' + dupeShown + ' possible duplicate' + (dupeShown > 1 ? 's' : '') : '';
      var filterNote = (activeType ? ' · showing ' + activeType : '') +
        (activeLoc ? ' · ' + (activeLoc === 'server' ? 'on server' : 'this device') : '') +
        (activeLabel ? ' · label: ' + activeLabel : '') +
        (qstr ? ' · "' + qstr + '"' : '');
      if (mode === 'server') {
        st.textContent = serverData.total + ' on server · ' + pendingCount + ' upload pending' +
          ' · ' + items.length + ' shown (' + typeLine + ')' + filterNote + orderNote + dupeNote;
      } else if (mode === 'offline') {
        st.textContent = q.length + ' on this device (server unreachable, will retry)' +
          ' · ' + items.length + ' shown (' + typeLine + ')' + filterNote + orderNote + dupeNote;
      } else {
        st.textContent = q.length + ' on this device only (no sync yet — tap Sync now)' +
          ' · ' + items.length + ' shown (' + typeLine + ')' + filterNote + orderNote + dupeNote;
      }
      var vl = SH.getElementById('verifyLine');
      if (vl) {
        if (verifyOn && newestSaved) {
          vl.style.display = '';
          vl.textContent = 'Newest saved: @' + (newestSaved.author || '?') +
            ' (saved #1) · Oldest: @' + ((oldestSaved && oldestSaved.author) || '?') +
            ' (saved #' + ranked.length + '). Compare with X order, newest first.';
        } else { vl.style.display = 'none'; vl.textContent = ''; }
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
    var ul = SH.getElementById('whList');
    var status = SH.getElementById('whStatus');
    if (!ul || !status) return;
    var seen = {};
    var urls = (local || []).map(function (w) { return typeof w === 'string' ? w : w.url; })
      .filter(Boolean).filter(function (u) {
        if (seen[u]) return false;
        seen[u] = true;
        return true;
      });
    ul.textContent = '';
    if (urls.length) urls.forEach(function (u) { ul.appendChild(mk('li', null, u)); });
    else ul.appendChild(mk('li', null, 'No webhook URLs yet. Add one above.'));
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
    var ul = SH.getElementById('labList');
    var status = SH.getElementById('labStatus');
    var counts = {};
    Object.keys(map).forEach(function (id) {
      (map[id] || []).forEach(function (l) { counts[l] = (counts[l] || 0) + 1; });
    });
    ul.textContent = '';
    if (!defs.length) { ul.appendChild(mk('li', null, 'No labels yet. Create one above.')); }
    defs.forEach(function (d) {
      var c = counts[d] || 0;
      var li = mk('li');
      li.appendChild(mk('span', 'nm', d));
      li.appendChild(mk('span', 'ct', c + ' saved' + (activeLabel === d ? ' · showing' : '')));
      var b = mk('button', null, activeLabel === d ? 'Clear' : 'Show');
      b.dataset.act = 'filter'; b.dataset.label = d;
      li.appendChild(b);
      ul.appendChild(li);
    });
    status.textContent = serverState === null
      ? 'Local-only (no API base + token in Sync tab).'
      : serverState === 'ok'
        ? defs.length + ' label(s), synced with server.'
        : defs.length + ' label(s), saved locally (server unreachable, will retry).';
    // filter dropdown in Saved pane
    var sel = SH.getElementById('labelFilter');
    var cur = activeLabel;
    sel.options.length = 0;
    sel.appendChild(new Option('All labels', ''));
    defs.forEach(function (d) {
      var o = new Option(d, d);
      if (d === cur) o.selected = true;
      sel.appendChild(o);
    });
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
    var ul = SH.getElementById('apList');
    var status = SH.getElementById('apStatus');
    if (!ul || !status) return;
    var items = (local || []).slice(-50).reverse();
    ul.textContent = '';
    if (items.length) items.forEach(function (p) {
      var st = p.status || 'pending';
      var li = mk('li');
      li.appendChild(mk('span', 't', p.title || '(untitled)'));
      li.appendChild(mk('span', 'st', st));
      if (st === 'pending') {
        var row = mk('div', 'row2');
        var ok = mk('button', null, 'Approve');
        ok.dataset.act = 'ap-approve'; ok.dataset.id = p.id;
        var no = mk('button', null, 'Reject');
        no.dataset.act = 'ap-reject'; no.dataset.id = p.id;
        row.appendChild(ok); row.appendChild(no);
        li.appendChild(row);
      }
      ul.appendChild(li);
    });
    else ul.appendChild(mk('li', null, 'No proposed actions. Propose one above to try the flow.'));
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

  SH.getElementById('whAdd').addEventListener('click', function () {
    var inp = SH.getElementById('whUrl');
    var url = String(inp.value || '').trim();
    if (!validWebhookUrl(url)) {
      var st0 = SH.getElementById('whStatus');
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
    var qstr = SH.getElementById('search').value;
    return Promise.all([getQueue(), getLabelMap(), getLabelDefs(), serverSearch(qstr, activeLabel)]).then(function (parts) {
      var q = parts[0], map = parts[1], defs = parts[2], serverData = parts[3];
      return render(q, map, qstr, serverData).then(function () {
        chrome.runtime.sendMessage({ type: 'bv-stats' }, function (s) {
          var h = SH.getElementById('health');
          if (!h) return;
          if (!s) { h.textContent = ''; return; }
          // HTTP preview has no background worker: fall back to the local queue count.
          if (typeof s.queued !== 'number') { h.textContent = 'Queue ' + q.length + ' · never synced'; return; }
          var m = s.meta || {}, st = s.status || {};
          var live = st.watching ? 'watching X now' : 'open x.com bookmarks or your profile likes to capture';
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

  SH.getElementById('labCreate').addEventListener('click', function () {
    var inp = SH.getElementById('labName');
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

  SH.getElementById('apAdd').addEventListener('click', function () {
    var inp = SH.getElementById('apTitle');
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

  SH.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.dataset || !t.dataset.act) return;
    var id = t.dataset.id, label = t.dataset.label;
    if (t.dataset.act === 'clear') {
      activeLabel = '';
      activeType = '';
      activeLoc = '';
      var si = SH.getElementById('search');
      if (si) si.value = '';
      var lf = SH.getElementById('labelFilter');
      if (lf) lf.value = '';
      var tf = SH.getElementById('typeFilter');
      if (tf) tf.value = '';
      var lf2 = SH.getElementById('locFilter');
      if (lf2) lf2.value = '';
      refresh();
    } else if (t.dataset.act === 'detach') {
      getLabelMap().then(function (map) {
        map[id] = (map[id] || []).filter(function (l) { return l !== label; });
        if (!map[id].length) delete map[id];
        return setLabelMap(map);
      }).then(function () { return serverDetach(id, label); }).then(refresh);
    } else if (t.dataset.act === 'attach') {
      var sel = SH.querySelector('select[data-attach-for="' + CSS.escape(id) + '"]');
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
    } else if (t.dataset.act === 'more') {
      var box = SH.querySelector('li[data-tid="' + CSS.escape(id) + '"] .txt');
      if (box) {
        var open = box.classList.toggle('expanded');
        box.classList.toggle('collapsed', !open);
        t.textContent = open ? 'Show less' : 'Show all';
      }
    } else if (t.dataset.act === 'filter') {
      activeLabel = (activeLabel === label) ? '' : label;
      // jump to Saved pane so the result is visible (no scroll steal: tab switch only)
      showPane('pane-saved', false);
      refresh();
    }
  });

  SH.getElementById('clearSearch').addEventListener('click', function () {
    activeLabel = '';
    activeType = '';
    activeLoc = '';
    SH.getElementById('search').value = '';
    SH.getElementById('labelFilter').value = '';
    SH.getElementById('typeFilter').value = '';
    SH.getElementById('locFilter').value = '';
    refresh(); // user-initiated: no scroll steal, list re-renders in place
  });
  SH.getElementById('typeFilter').addEventListener('change', function (ev) {
    activeType = ev.target.value || '';
    refresh();
  });
  SH.getElementById('locFilter').addEventListener('change', function (ev) {
    activeLoc = ev.target.value || '';
    refresh();
  });
  try {
    chrome.storage.local.get('bv.verifyOrder').then(function (o) {
      verifyOn = !!(o && o['bv.verifyOrder']);
      var cb = SH.getElementById('verifyOrder');
      if (cb) cb.checked = verifyOn;
    });
  } catch (e) {}
  SH.getElementById('verifyOrder').addEventListener('change', function (ev) {
    verifyOn = !!ev.target.checked;
    try { chrome.storage.local.set({ 'bv.verifyOrder': verifyOn }); } catch (e) {}
    refresh();
  });
  SH.getElementById('labelFilter').addEventListener('change', function (ev) {
    activeLabel = ev.target.value || '';
    refresh();
  });

  var searchTimer = null;
  SH.getElementById('search').addEventListener('input', function () {
    // Debounced so each keystroke does not hammer GET /v1/bookmarks; no scroll steal.
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(refresh, 250);
  });
  chrome.storage.onChanged.addListener(function (chg) {
    if (chg['bv.verifyOrder']) { verifyOn = !!(chg['bv.verifyOrder'].newValue); refresh(); return; }
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
    var el = SH.getElementById('impStatus');
    var bs = SH.getElementById('impStart');
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
  function refreshImport() {
    return Promise.all([getImport(), getQueue()]).then(function (parts) {
      renderImport(parts[0]);
      var bar = SH.getElementById('impBar');
      if (bar) {
        var sc = (parts[0] && parts[0].scrolls) || 0;
        bar.style.width = Math.min(100, Math.round(sc / 15)) + '%'; // 1500 max scrolls
      }
      var qb = SH.getElementById('impQueue');
      if (qb) {
        var b = 0, l = 0, bo = 0;
        parts[1].forEach(function (r) {
          var st = statusOf(r);
          if (st === 'both') bo++;
          else if (st === 'liked') l++;
          else if (st === 'saved') b++;
        });
        qb.textContent = parts[1].length
          ? 'Waiting on this device: ' + bo + ' liked+bookmarked · ' + l + ' liked · ' + b + ' bookmarked.'
          : 'Queue empty — everything captured is on the server (or nothing captured yet).';
      }
    });
  }
  var __impStart = SH.getElementById('impStart');
  if (__impStart) __impStart.addEventListener('click', function () {
    getImport().then(function (cur) {
      var fresh = (!cur || cur.state === 'done')
        ? { wish: 'run', state: 'running', scrolls: 0, captured: 0, checkpointY: 0, checkpointId: '', reason: '', cooldownUntil: 0 }
        : { wish: 'run', state: 'running', reason: '', cooldownUntil: 0 };
      return setImport(fresh);
    });
  });
  var __impPause = SH.getElementById('impPause');
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
    var el = SH.getElementById('plan');
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

  SH.getElementById('save').addEventListener('click', function () {
    var apiBase = SH.getElementById('apiBase').value.trim();
    var token = SH.getElementById('token').value.trim();
    chrome.storage.local.set({ 'bv.apiBase': apiBase, 'bv.token': token }).then(function () {
      SH.getElementById('status').textContent = apiBase && token ? 'Settings saved.' : 'Cleared — staying local-only.';
      fetchPlan();
      refresh();
    });
  });
  SH.getElementById('planBtn').addEventListener('click', fetchPlan);
  chrome.storage.local.get('bv.devMode').then(function (o) {
    SH.getElementById('devMode').checked = !!o['bv.devMode'];
  });
  SH.getElementById('devMode').addEventListener('change', function (e) {
    chrome.runtime.sendMessage({ type: 'bv-devmode', on: e.target.checked }, function () {
      SH.getElementById('tuneHint').textContent = e.target.checked
        ? 'Dev mode ON: tuning loads from server. Tap Refresh tuning, then scroll.'
        : 'Off = store build (frozen).';
    });
  });
  SH.getElementById('tuneBtn').addEventListener('click', function () {
    SH.getElementById('tuneHint').textContent = 'Fetching…';
    chrome.runtime.sendMessage({ type: 'bv-tuning-refresh' }, function (r) {
      SH.getElementById('tuneHint').textContent = r && r.ok
        ? 'Tuning v' + r.v + ' applied. Scroll to feel it.'
        : 'Server unreachable — frozen tuning stays.';
    });
  });
  function installedVer() {
    try { return 'v' + chrome.runtime.getManifest().version; }
    catch (e) { return 'preview'; }
  }
  function checkVersions() {
    var box = SH.getElementById('buildBox');
    var inst = installedVer();
    box.textContent = 'This extension: ' + inst + ' · checking published…';
    getApi().then(function (a) {
      var ops = (a.apiBase || DEFAULT_BASE).replace(/:8899\/?$/, ':8901');
      if (!/:8901/.test(ops)) ops = OPS_BASE;
      var lane = SH.getElementById('devMode').checked
        ? 'Logic lane: REMOTE (auto-updates ON)'
        : 'Logic lane: FROZEN bundled copy (turn on Developer mode)';
      return Promise.all([
        Promise.all([
          fetch(ops.replace(/\/$/, '') + '/ext/manifest.json').then(function (r) {
            if (!r.ok) throw new Error('http-' + r.status);
            return r.json();
          }).then(function (m) { return 'v' + (m.version || '?'); }).catch(function () { return null; }),
          fetch(ops.replace(/\/$/, '') + '/ext/build.json').then(function (r) {
            return r.json();
          }).then(function (b) { return b.built_at || null; }).catch(function () { return null; })
        ]).then(function (parts) { return { ver: parts[0], built: parts[1] }; }),
        chrome.storage.local.get('bv.tuning').then(function (o) {
          var t = o && o['bv.tuning'];
          return lane + (t && t.v ? ', tuning v' + t.v : '');
        }),
        fetch((a.apiBase || DEFAULT_BASE).replace(/\/$/, '') + '/health').then(function (r) {
          return r.json();
        }).then(function (h) { return 'Server: ' + (h.version || '?') + ' (' + (h.mode || '?') + ')'; })
        .catch(function () { return 'Server: unreachable'; })
      ]).then(function (parts) {
        var pub = parts[0] && parts[0].ver, built = parts[0] && parts[0].built,
            laneLine = parts[1], srv = parts[2];
        var when = built ? ' (built ' + fmtBuild(built) + ')' : '';
        var upd = !pub ? ' · published: unreachable (ops server down?)'
          : (pub === inst ? ' · published ' + pub + when + ' — YOU ARE UP TO DATE'
          : ' · published ' + pub + when + ' — UPDATE AVAILABLE (refresh files + reload, same folder!)');
        box.textContent = 'This extension: ' + inst + upd + '\n' + laneLine + '\n' + srv;
      });
    });
  }
  SH.getElementById('verCheck').addEventListener('click', checkVersions);
  SH.getElementById('sync').addEventListener('click', function () {
    SH.getElementById('status').textContent = 'Syncing…';
    chrome.runtime.sendMessage({ type: 'bv-sync-now' }, function (r) {
      SH.getElementById('status').textContent = r && r.ok
        ? 'Synced ' + (r.synced || 0) + ' bookmark(s).'
        : 'Still local (' + ((r && r.reason) || 'no connection') + '). Nothing lost.';
      refresh();
    });
  });
  SH.getElementById('wipe').addEventListener('click', function () {
    if (!confirm('Erase ALL saved tweets on this device AND on the server? Labels stay.')) return;
    var keys = [QUEUE_KEY, LABELS_KEY, IMPORT_KEY];
    chrome.storage.local.remove(keys, function () {
      getApi().then(function (a) {
        if (!a.apiBase || !a.token) { refresh(); refreshImport(); return; }
        fetch(a.apiBase.replace(/\/$/, '') + '/v1/bookmarks/all', {
          method: 'DELETE',
          headers: { Authorization: 'Bearer ' + a.token }
        }).then(function () { refresh(); refreshImport(); })
        .catch(function () { refresh(); refreshImport(); });
      });
    });
  });
  SH.getElementById('dl').addEventListener('click', function () {
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

  getApi().then(function (a) {
    SH.getElementById('apiBase').value = a.apiBase;
    SH.getElementById('token').value = a.token;
    var vs = SH.getElementById('viewServer');
    if (vs && a.apiBase) vs.href = a.apiBase.replace(/\/$/, '') + '/view';
  });
  refresh();
  refreshImport();
  fetchPlan();
  checkVersions();

  
    try { window.BVAPP.refresh = refresh; } catch (e) {}
  }
