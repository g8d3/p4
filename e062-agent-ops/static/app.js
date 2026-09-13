// Fleet board UI: three verbs — steer (pause/resume), help (notes), approve (money).
// All DOM writes happen inside functions. No top-level data references.
function tok() {
  let t = localStorage.bt;
  if (!t) { t = prompt('board token — shown once in owner chat:'); if (t) localStorage.bt = t.trim(); }
  return (localStorage.bt || '').trim();
}
function setToken(btn) {
  const cur = localStorage.bt || '';
  const t = prompt('board token:', cur ? '••••' + cur.slice(-4) : '');
  if (t === null) return;
  const v = (t || '').trim();
  const old = 'token';
  if (!v) { delete localStorage.bt; btn.textContent = 'cleared'; }
  else { localStorage.bt = v; btn.textContent = 'saved ✓'; }
  setTimeout(() => { btn.textContent = old; }, 2500);
}
async function ctl(path, body, btn, okmsg, _retried) {
  let t = tok();
  if (!t) return;
  const old = btn.textContent;
  btn.textContent = '…'; btn.disabled = true;
  try {
    const r = await (await fetch(path, {method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Token': t},
      body: JSON.stringify(body)})).json();
    if (r.ok) { btn.textContent = okmsg || 'done ✓'; load(); }
    else if (!_retried && /bad token/i.test(r.error || '')) {
      // stale/wrong saved token: drop it, ask once, retry automatically
      delete localStorage.bt;
      alert('saved board token was wrong — enter the current one:');
      const v = (prompt('board token:') || '').trim();
      if (v) { localStorage.bt = v; btn.textContent = old; btn.disabled = false; return ctl(path, body, btn, okmsg, true); }
      btn.textContent = 'error';
    }
    else { btn.textContent = 'error'; alert(r.error || 'failed'); }
  } catch (e) { btn.textContent = 'error'; alert(String(e)); }
  setTimeout(() => { btn.textContent = old; btn.disabled = false; }, 2500);
}
async function openCtl(path, body, btn, okmsg) {
  const old = btn.textContent;
  btn.textContent = '…'; btn.disabled = true;
  try {
    const r = await (await fetch(path, {method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)})).json();
    if (r.ok) { btn.textContent = okmsg || 'done ✓'; load(); }
    else { btn.textContent = 'error'; alert(r.error || 'failed'); }
  } catch (e) { btn.textContent = 'error'; alert(String(e)); }
  setTimeout(() => { btn.textContent = old; btn.disabled = false; }, 2500);
}
function togPause(t, btn) {
  const paused = (window._paused || []).includes(t);
  openCtl(paused ? '/api/resume' : '/api/pause', {track: t}, btn, paused ? 'resumed ✓' : 'paused ✓');
}
function runScope(t, btn) { openCtl('/api/run', {scope: t}, btn, 'leg started ✓'); }
function runFleet(btn) { openCtl('/api/run', {scope: 'fleet'}, btn, 'leg started ✓'); }
function splitOwnerTech(s) {
  s = String(s == null ? '' : s);
  const i = s.indexOf(' | ');
  if (i < 0) return {owner: s, tech: s};
  return {owner: s.slice(0, i).trim(), tech: s.slice(i + 3).trim()};
}
function fmtDetail(s) {
  const m = window._report || 'simple';
  const p = splitOwnerTech(s);
  if (m === 'tech') return p.tech;
  if (m === 'both') return (p.owner === p.tech) ? p.owner : (p.owner + ' | ' + p.tech);
  return p.owner;
}
function paintReportSeg() {
  const m = window._report || 'simple';
  document.querySelectorAll('.seg button[data-v]').forEach(function(b) {
    b.classList.toggle('on', b.getAttribute('data-v') === m);
  });
}
async function setReport(v, btn) {
  window._report = v;
  paintReportSeg();
  try {
    await fetch('/api/prefs', {method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({report: v})});
  } catch (e) {}
  load();
}
function saveDrafts() {
  const m = {};
  document.querySelectorAll('input[id^="n-"]').forEach(i => { m[i.id] = i.value; });
  return m;
}
function restoreDrafts(m) {
  for (const k in m) {
    const el = document.getElementById(k);
    if (el && document.activeElement !== el) el.value = m[k];
  }
}
function decide(id, v, btn) { ctl('/api/decide', {id: id, verdict: v}, btn, v + ' ✓'); }
async function sendNoteQueued(t, btn) {
  const inp = document.getElementById('n-' + t);
  const v = inp.value.trim();
  if (!v) return;
  const old = btn.textContent;
  btn.textContent = '…'; btn.disabled = true;
  try {
    const r = await (await fetch('/api/note', {method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({track: t, message: v})})).json();
    if (r.ok) { inp.value = ''; btn.textContent = 'queued ✓'; load(); }
    else { btn.textContent = 'error'; alert(r.error || 'failed'); }
  } catch (e) { btn.textContent = 'error'; alert(String(e)); }
  setTimeout(() => { btn.textContent = old; btn.disabled = false; }, 2500);
}
async function sendNoteRun(t, btn) {
  const inp = document.getElementById('n-' + t);
  const v = inp.value.trim();
  if (!v) { alert('write the message first — or use plain run for no-message'); return; }
  const old = btn.textContent;
  btn.textContent = 'sending…'; btn.disabled = true;
  try {
    const r1 = await (await fetch('/api/note', {method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({track: t, message: v})})).json();
    if (!r1.ok) { btn.textContent = 'error'; alert(r1.error || 'note failed'); }
    else {
      inp.value = '';
      btn.textContent = 'starting…';
      const r2 = await (await fetch('/api/run', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({scope: t})})).json();
      if (r2.ok) { btn.textContent = 'running ✓'; load(); }
      else { btn.textContent = 'error'; alert((r2.error || 'run failed') + ' — message was queued anyway'); }
    }
  } catch (e) { btn.textContent = 'error'; alert(String(e)); }
  setTimeout(() => { btn.textContent = old; btn.disabled = false; }, 2500);
}
function esc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
}
async function load() {
  if (window._wrap === undefined) window._wrap = true;
  const drafts = saveDrafts();
  const ae = document.activeElement;
  const typing = ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA') && ae.value;
  const d = await (await fetch('/api/board')).json();
  window._paused = d.paused || [];
  window._board = d;
  try { window._report = (d.prefs && d.prefs.report) || window._report || 'simple'; } catch (e) {}
  try { paintReportSeg(); } catch (e) {}
  try {
    const _d = new Date(), _p = function(n) { return (n < 10 ? '0' : '') + n; };
    document.getElementById('ts').textContent = _p(_d.getHours()) + ':' + _p(_d.getMinutes()) + ' local';
  } catch (e) {}
  const waitByTrack = {};
  (d.notes || []).forEach(n => { waitByTrack[n.track] = (waitByTrack[n.track] || 0) + 1; });
  (d.proposals || []).filter(p => p.status === 'pending').forEach(p => { waitByTrack[p.track] = (waitByTrack[p.track] || 0) + 1; });
  const waitTotal = Object.keys(waitByTrack).reduce((a, k) => a + waitByTrack[k], 0);
  document.getElementById('cards').innerHTML = d.tracks.map(t => {
    const paused = (d.paused || []).includes(t.track);
    const open = window._openCard === t.track;
    return '<div class="card' + (open ? ' open' : '') + '" id="c-' + t.track + '">' +
    '<div class=chead onclick="toggleCard(\'' + t.track + '\')">' +
    '<span class=ctrack>' + esc(t.track) + '</span><span>' + esc(t.label) + '</span>' +
    '<span class="rung ' + (t.rung > 0 ? 'r1' : 'r0') + '">rung ' + t.rung + '</span>' +
    ((waitByTrack[t.track] || 0) ? '<button class=needbadge title="notes + money gates waiting for you — tap to see" onclick="event.stopPropagation();waitFor(\'' + t.track + '\')">●' + waitByTrack[t.track] + ' waiting</button>' : '') +
    (paused ? '<span class=pausedtag>paused</span>' : '') +
    '<span style="margin-left:auto;font-size:11px;opacity:.6">' + (open ? '▾ close' : '▸ history + message') + '</span></div>' +
    '<div class=cbeat><span style="font-size:10px;opacity:.55">last:</span> ' + esc(t.beat ? (shortTime(t.beat.ts) + ' ' + t.beat.status + ' ' + fmtDetail(t.beat.note)) : '\u2014') + '</div>' +
    (t.url ? '<div style="font-size:12px"><span style="font-size:10px;opacity:.55">link:</span> <a href="' + esc(t.url) + '" onclick="event.stopPropagation()">' + esc(t.url) + '</a></div>' : '') +
    '<div class=rowbtns style="margin-top:6px" onclick="event.stopPropagation()">' +
    '<button onclick="togPause(\'' + t.track + '\',this)">' + (paused ? 'resume' : 'pause') + '</button> ' +
    '<button onclick="runScope(\'' + t.track + '\',this)" title="run now WITHOUT any message">run</button></div>' +
    (open ? cardDetail(t) : '') +
    '</div>';
  }).join('');
  restoreDrafts(drafts);
  if (typing) { const el = document.getElementById(ae.id); if (el) { el.focus(); if (el.setSelectionRange && el.value) try { el.setSelectionRange(el.value.length, el.value.length); } catch (e) {} } }
  const rs = document.getElementById('runstate');
  if (rs) rs.innerHTML = runPill(d);
  try { renderLive(d); } catch (e) {}
  const wt = document.getElementById('waiting');
  if (wt) wt.title = 'your notes + money gates waiting for a tap';
  if (wt) { wt.style.display = waitTotal ? '' : 'none'; } if (wt) wt.textContent = waitTotal ? ('● ' + waitTotal + ' waiting \u2014 tap to see') : '';
  document.getElementById('w').textContent =
    'treasury: spent $' + d.runway.spent.toFixed(2) + ' earned $' + d.runway.earned.toFixed(2) +
    ' left $' + d.runway.left.toFixed(2) + ' of $300';
  try { window._unirows = buildUnified(d); loadWidgets(d); renderWidgets(); } catch (e) {}
  try { renderGates(d); } catch (e) {}
  try { renderLists(d); } catch (e) {}
  const leg = document.getElementById('leg');
  if (leg) leg.textContent = d.leg_tail || 'no log yet';
  const tsum = document.getElementById('trials-sum');
  if (tsum) tsum.textContent = (d.trials || []).length ? (d.trials.length + ' active trials — tap to read') : 'trials — none active';
  const isum = document.getElementById('ideas-sum');
  if (isum) isum.textContent = (d.ideas || []).length ? (d.ideas.length + ' ideas — tap to read') : 'ideas inbox — empty';
  const dsum = document.getElementById('dir-sum');
  if (dsum) dsum.textContent = 'standing orders — tap to read';
}
function toggleCard(t) {
  window._openCard = (window._openCard === t) ? null : t;
  load();
}
function cardHist(track) {
  const d = window._board || {events: [], runs: [], notes: []};
  const items = [];
  (d.events || []).filter(e => e.track === track).forEach(e =>
    items.push({time: e.ts, kind: e.kind, text: e.summary}));
  (d.runs || []).filter(r => r.scope === track).forEach(r =>
    items.push({time: r.started || '', kind: 'run #' + r.id + ' \u00b7 ' + (r.status || ''), text: runLine(r), leg: r.id}));
  (d.notes || []).filter(n => n.track === track).forEach(n =>
    items.push({time: n.ts, kind: 'owner note', text: n.message}));
  items.sort((a, b) => (b.time || '') < (a.time || '') ? -1 : 1);
  return items.slice(0, 15);
}
function cardDetail(t) {
  const items = cardHist(t.track);
  const h = items.length ? items.map(x =>
    '<div><b>' + esc(x.time || '') + '</b> [' + esc(x.kind || '') + '] ' + esc(fmtDetail(x.text || '')) +
    (x.leg ? ' <a href="/api/leg/' + x.leg + '" target=_blank>log</a>' : '') + '</div>'
  ).join('') : '<div>no history yet</div>';
  return '<div class=cdetail onclick="event.stopPropagation()">' +
    '<div style="font-size:12px;opacity:.8"><span style="font-size:10px;opacity:.55">plan:</span> ' + esc(t.plan || '') + '</div>' +
    '<div style="font-size:12px;margin-top:6px"><b>history</b> (this project only)</div>' +
    '<div class=hist>' + h + '</div>' +
    '<div style="font-size:12px"><b>message to the ' + esc(t.track) + ' agent</b> \u2014 one box, you decide when it runs:</div>' +
    '<div class=msgrow><input id="n-' + t.track + '" placeholder="what should the agent do\u2026"></div>' +
    '<div class=rowbtns style="margin-top:4px">' +
    '<button onclick="sendNoteQueued(\'' + t.track + '\',this)">queue (next leg)</button> ' +
    '<button onclick="sendNoteRun(\'' + t.track + '\',this)">send + run now</button></div>' +
    '<div style="font-size:11px;opacity:.6">queue = read whenever the next leg runs. send + run now = your message starts a leg immediately on this project. plain run (above) starts a leg with NO message.</div></div>';
}
function actTs(s) {
  try { return new Date(String(s).replace(' ', 'T') + 'Z').getTime(); } catch (e) { return 0; }
}
function runLine(r) {
  // OWNER-FIRST: plain sentence before ' | ', tech detail after — simple mode
  // shows only the plain half (thumb-readable in <30s), tech one tap away.
  const w = worked(r);
  const owner = 'Run #' + r.id + ' ' + (r.status || 'done') + (w !== '—' ? ' in ' + w : '');
  const bits = [];
  if (r.tokens != null) bits.push(Number(r.tokens).toLocaleString() + ' tok');
  if (r.tok_s != null) bits.push(r.tok_s + ' tok/s');
  if (r.cost_usd != null) bits.push('$' + Number(r.cost_usd).toFixed(4));
  if (r.scope) bits.push(r.scope + '/' + (r.trigger || ''));
  if (r.session) bits.push('ses ' + r.session);
  if (r.summary) bits.push(r.summary);
  return bits.length ? (owner + ' | tech: ' + bits.join(' · ')) : owner;
}
function worked(r) {
  try {
    if (!r.started) return '—';
    const t0 = new Date(r.started.replace(' ', 'T') + 'Z').getTime();
    const t1 = r.ended ? new Date(r.ended.replace(' ', 'T') + 'Z').getTime() : Date.now();
    const s = Math.max(0, Math.round((t1 - t0) / 1000));
    if (s < 60) return s + 's';
    const m = Math.floor(s / 60);
    return m + 'm ' + (s % 60) + 's';
  } catch (e) { return '—'; }
}
function runPill(d) {
  const r = d.runner || {};
  if (r.running) {
    return '<span style="color:#1a9e4b;font-weight:bold">● RUNNING' +
      (r.run_id ? ' #' + r.run_id : '') +
      (r.scope ? ' · ' + esc(r.scope) : '') +
      (r.trigger ? ' · ' + esc(r.trigger) : '') +
      (r.started ? ' · ' + elapsedMin(r.started) : '') + '</span>';
  }
  return '<span style="opacity:.55">○ idle' +
    (r.run_id ? ' · last #' + r.run_id + ' ' + esc(r.status || 'done') : '') + '</span>';
}
function elapsedMin(s) {
  try {
    const m = Math.max(0, Math.round((Date.now() - new Date(s.replace(' ', 'T') + 'Z').getTime()) / 60000));
    return m < 1 ? '<1m' : m + 'm';
  } catch (e) { return ''; }
}
function readTune() {
  return {font: document.getElementById('pf').value, planw: document.getElementById('pw').value,
    beatw: document.getElementById('bw').value, urlw: document.getElementById('uw').value,
    ctrlw: document.getElementById('cw').value, rowpad: document.getElementById('rp').value,
    wrap: document.getElementById('wr').value, density: document.getElementById('pd').value};
}
function paintTune(v) {
  const r = document.documentElement.style;
  r.setProperty('--fs', v.font + 'px');
  r.setProperty('--planw', v.planw + 'px');
  r.setProperty('--beatw', v.beatw + 'px');
  r.setProperty('--urlw', v.urlw + 'px');
  r.setProperty('--ctrlw', v.ctrlw + 'px');
  r.setProperty('--rowpad', v.rowpad + 'px');
  window._wrap = String(v.wrap) === '1';
  document.body.classList.toggle('compact', v.density === 'compact');
  for (const k of ['font', 'planw', 'beatw', 'urlw', 'ctrlw', 'rowpad', 'wrap', 'density']) {
    const map = {font: 'pf', planw: 'pw', beatw: 'bw', urlw: 'uw', ctrlw: 'cw', rowpad: 'rp', wrap: 'wr', density: 'pd'};
    const el = document.getElementById(map[k]);
    if (el) el.value = v[k];
  }
}
async function applyPrefs() {
  try {
    const d = await (await fetch('/api/prefs')).json();
    paintTune(d.prefs);
  } catch (e) {}
}
async function savePrefs(btn) {
  btn.textContent = '…';
  const r = await (await fetch('/api/prefs', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(readTune())})).json();
  const s = document.getElementById('psaved');
  if (r.ok) { btn.textContent = 'save'; s.textContent = 'saved ✓'; }
  else { btn.textContent = 'save'; s.textContent = 'failed'; }
  setTimeout(() => { s.textContent = ''; }, 2500);
}
load();
setInterval(() => {
  const a = document.activeElement;
  if (a && (a.tagName === 'INPUT' || a.tagName === 'TEXTAREA') && a.value) return;
  load();
}, 60000);

/* ---- views: configurable widgets over one unified flow ---- */
function defaultWidgets() {
  return [
    {t: 'all', q: '', g: 'none', s: 'new', n: 20, p: 0, open: -1},
    {t: 'by project', q: '', g: 'project', s: 'new', n: 20, p: 0, open: -1},
    {t: 'money', q: 'money gate', g: 'project', s: 'new', n: 20, p: 0, open: -1},
    {t: 'waiting', q: 'is:waiting', g: 'project', s: 'new', n: 20, p: 0, open: -1}
  ];
}
function cleanWidget(w) {
  w = w || {};
  return {t: String(w.t || 'view').slice(0, 40), q: String(w.q || '').slice(0, 140),
    g: ['none', 'project', 'session', 'kind'].indexOf(w.g) >= 0 ? w.g : 'none',
    s: w.s === 'old' ? 'old' : 'new',
    n: [10, 20, 50].indexOf(w.n) >= 0 ? w.n : 20, p: 0, open: -1};
}
function buildUnified(d) {
  const rows = [];
  (d.runs || []).forEach(function(r) {
    const track = r.scope === 'fleet' ? 'runner' : (r.scope || '');
    const ses = r.session ? ('run #' + r.id + ' \u00b7 ses ' + String(r.session).replace(/,/g, ' +')) : ('run #' + r.id);
    rows.push({t: actTs(r.started), time: r.started || '', track: track,
      kind: 'session', session: ses,
      detail: runLine(r), full: runLine(r), leg: r.id, wait: 0, runid: r.id, sesid: (r.session || '')});
  });
  (d.events || []).forEach(function(e) { rows.push({t: actTs(e.ts), time: e.ts, track: e.track,
    kind: e.kind, session: '', detail: e.summary, full: e.summary, leg: null, wait: 0}); });
  (d.notes || []).forEach(function(n) { rows.push({t: actTs(n.ts), time: n.ts, track: n.track,
    kind: 'owner note', session: '', detail: n.message, full: n.message, leg: null, wait: 1}); });
  (d.proposals || []).forEach(function(pr) { rows.push({t: actTs(pr.ts), time: pr.ts, track: pr.track,
    kind: 'money gate', session: 'gate #' + pr.id,
    detail: '#' + pr.id + ' $' + pr.usd + ' ' + pr.action + ' \u2014 ' + pr.reason + ' (' + pr.status + ')',
    full: '#' + pr.id + ' $' + pr.usd + ' ' + pr.action + ' \u2014 ' + pr.reason + ' (' + pr.status + ')',
    leg: null, wait: pr.status === 'pending' ? 1 : 0,
    propId: pr.id, propPending: pr.status === 'pending'}); });
  return rows;
}
function loadWidgets(d) {
  if (window._widgets && window._widgets.length) return;
  try {
    const w = JSON.parse((d.prefs && d.prefs.widgets) || '');
    if (Array.isArray(w) && w.length <= 12) { window._widgets = w.map(cleanWidget); return; }
  } catch (e) {}
  window._widgets = defaultWidgets();
}
function slimWidgets() {
  return (window._widgets || []).map(function(w) { return {t: w.t, q: w.q, g: w.g, s: w.s, n: w.n}; });
}
async function saveWidgets() {
  try {
    await fetch('/api/prefs', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({widgets: JSON.stringify(slimWidgets())})});
  } catch (e) {}
}
let _wsave = null;
function saveWidgetsSoon() { try { clearTimeout(_wsave); } catch (e) {} _wsave = setTimeout(saveWidgets, 1200); }
function widgetRows(w) {
  // mini query: space-separated AND tokens; is:waiting = needs your tap
  const toks = String(w.q || '').toLowerCase().split(/\s+/).filter(Boolean);
  let rows = (window._unirows || []).slice();
  toks.forEach(function(tok) {
    if (tok === 'is:waiting') rows = rows.filter(function(r) { return r.wait; });
    else rows = rows.filter(function(r) {
      return ((r.track || '') + ' ' + (r.kind || '') + ' ' + (r.session || '') + ' ' + (r.detail || '')).toLowerCase().indexOf(tok) >= 0;
    });
  });
  rows.sort(function(a, b) { return w.s === 'old' ? (a.t - b.t) : (b.t - a.t); });
  return rows;
}
function selOpts(wi, field, opts) {
  const cur = window._widgets[wi][field];
  return opts.map(function(o) {
    return '<option value=' + o[0] + (String(cur) === String(o[0]) ? ' selected' : '') + '>' + o[1] + '</option>';
  }).join('');
}
function widgetHTML(w, wi) {
  return '<div style="border:1px solid var(--bd);border-radius:8px;padding:6px;margin-bottom:8px">' +
  '<div style="display:flex;gap:6px;align-items:center">' +
  '<input value="' + esc(w.t).replace(/"/g, '&quot;') + '" oninput="wTitle(' + wi + ',this)" style="font-weight:bold;flex:1;min-width:80px" aria-label="view name">' +
  '<button onclick="wRemove(' + wi + ')" title="remove this view">×</button></div>' +
  '<div style="display:flex;gap:6px;flex-wrap:wrap;margin:4px 0">' +
  '<input value="' + esc(w.q).replace(/"/g, '&quot;') + '" placeholder="filter… (try is:waiting)" oninput="wSet(' + wi + ',\'q\',this)" style="flex:2;min-width:110px" aria-label="filter">' +
  '<select onchange="wSet(' + wi + ',\'g\',this)" aria-label="group by">' + selOpts(wi, 'g', [['none', 'group: none'], ['project', 'group: project'], ['session', 'group: session'], ['kind', 'group: kind']]) + '</select>' +
  '<select onchange="wSet(' + wi + ',\'s\',this)" aria-label="sort">' + selOpts(wi, 's', [['new', 'newest'], ['old', 'oldest']]) + '</select>' +
  '<select onchange="wSet(' + wi + ',\'n\',this)" aria-label="per page">' + selOpts(wi, 'n', [[10, '10/page'], [20, '20/page'], [50, '50/page']]) + '</select></div>' +
  '<div class=wlist id="wc-' + wi + '"></div>' +
  '<div class=rowbtns style="margin-top:6px;display:flex;gap:8px;align-items:center">' +
  '<button onclick="wPage(' + wi + ',-1)">‹ prev</button><span id="wi-' + wi + '" style="font-size:12px;opacity:.7"></span><button onclick="wPage(' + wi + ',1)">next ›</button></div></div>';
}
function renderWidgets() {
  const box = document.getElementById('widgets');
  if (!box || !window._widgets) return;
  if (!window._widgets.length) {
    box.innerHTML = '<div style="font-size:12px;opacity:.6">no views — add one above: +all, +project, +money or +waiting.</div>';
    return;
  }
  box.innerHTML = window._widgets.map(widgetHTML).join('');
  window._widgets.forEach(function(w, wi) { renderWidgetCards(wi); });
}
function shortTime(t) {
  // server stores UTC; the phone/computer shows ITS local time — no more UTC math
  try {
    const d = new Date(String(t).replace(' ', 'T') + 'Z');
    if (isNaN(d)) return String(t || '');
    const p = function(n) { return (n < 10 ? '0' : '') + n; };
    return p(d.getMonth() + 1) + '/' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  } catch (e) { return String(t || ''); }
}
function sesChips(wi, r) {
  if (r.kind === 'session' && r.runid) {
    let h = '<button onclick="event.stopPropagation();sesFilter(' + wi + ',' + "'" + 'run #' + r.runid + "'" + ')" title="show this leg\u2019s rows">run #' + r.runid + '</button>';
    if (r.sesid) {
      const first = String(r.sesid).split(',')[0];
      h += ' <button onclick="event.stopPropagation();sesFilter(' + wi + ',' + "'" + 'ses ' + first + "'" + ')" title="pi harness session id \u2014 tap to isolate">ses ' + first + '</button>' +
        (String(r.sesid).indexOf(',') >= 0 ? ' +' + (String(r.sesid).split(',').length - 1) : '');
    }
    return h;
  }
  return '<span style="font-size:11px;opacity:.6">' + esc(r.session || '\u2014') + '</span>';
}
function sesFilter(wi, q) {
  const w = window._widgets[wi];
  if (!w) return;
  w.q = q; w.p = 0; w.open = -1;
  saveWidgets(); renderWidgets();
}

function groupKey(r, g) {
  if (g === 'project') return r.track || '?';
  if (g === 'session') return r.session || r.kind || '?';
  if (g === 'kind') return r.kind || '?';
  return '';
}
function rowCard(wi, r, uid) {
  const w = window._widgets[wi];
  const open = w.open === uid;
  return '<div class="card' + (open ? ' open' : '') + '" onclick="wToggleRow(' + wi + ',\'' + uid + '\')">' +
    '<div class=frow><span>' + esc(shortTime(r.time)) + '</span>' +
    '<span class=ctrack>' + esc(r.track) + '</span><span>' + esc(r.kind) + '</span>' +
    '<span class=ses>' + sesChips(wi, r) + '</span>' +
    '<span>' + (r.wait ? '<span class=needbadge>waiting</span>' : '') + '</span></div>' +
    '<div class=cbeat>' + esc(fmtDetail(r.detail)) + '</div>' +
    (r.propPending ? '<div class=rowbtns style="margin-top:4px" onclick="event.stopPropagation()">' +
      '<button onclick="decide(' + r.propId + ',\'approved\',this)">approve</button>' +
      '<button onclick="decide(' + r.propId + ',\'rejected\',this)">reject</button></div>' : '') +
    (open ? uniDetail(r, uid) : '') + '</div>';
}
function groupRows(rows, g) {
  const map = {}, order = [];
  rows.forEach(function(r) {
    const k = groupKey(r, g);
    if (!map[k]) { map[k] = {key: k, rows: [], latest: 0, wait: 0}; order.push(k); }
    map[k].rows.push(r);
    if (r.t > map[k].latest) map[k].latest = r.t;
    if (r.wait) map[k].wait++;
  });
  return order.map(function(k) { return map[k]; }).sort(function(a, b) { return b.latest - a.latest; });
}
function groupTime(g) {
  try {
    const d = new Date(g.latest);
    const p = function(n) { return (n < 10 ? '0' : '') + n; };
    return p(d.getMonth() + 1) + '/' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  } catch (e) { return ''; }
}
function groupCard(wi, g, ggi) {
  const w = window._widgets[wi];
  const open = w.openGroup === ggi;
  return '<div class="card' + (open ? ' open' : '') + '" onclick="wToggleGroup(' + wi + ',' + ggi + ')">' +
    '<div class=chead><span class=ctrack>' + esc(g.key) + '</span>' +
    '<span style="font-size:12px;opacity:.75">' + g.rows.length + ' rows' + (g.wait ? ' · ' + g.wait + ' waiting' : '') + '</span>' +
    (g.wait ? '<span class=needbadge>waiting</span>' : '') +
    '<span style="margin-left:auto;font-size:11px;opacity:.6">' + esc(groupTime(g)) + (open ? ' ▾ close' : ' ▸ open') + '</span></div></div>';
}
function renderWidgetCards(wi) {
  const w = window._widgets[wi];
  const box = document.getElementById('wc-' + wi);
  if (!w || !box) return;
  const rows = widgetRows(w);
  const head = '<div class=whead><div class=frow><span>TIME</span><span>PROJECT</span><span>KIND</span><span>SESSION</span><span>WAIT</span></div></div>';
  if (w.g === 'none') {
    const maxp = Math.max(0, Math.ceil(rows.length / w.n) - 1);
    w.p = Math.min(w.p || 0, maxp);
    const page = rows.slice(w.p * w.n, w.p * w.n + w.n);
    box.innerHTML = head + (page.map(function(r, i) { return rowCard(wi, r, 'r' + (w.p * w.n + i)); }).join('') ||
      '<div style="font-size:12px;opacity:.6">no matches — clear the filter</div>');
    const info = document.getElementById('wi-' + wi);
    if (info) info.textContent = rows.length + ' rows · page ' + (w.p + 1) + '/' + Math.max(1, Math.ceil(rows.length / w.n));
    return;
  }
  // grouped: ONE card per group, tap to expand its rows
  const groups = groupRows(rows, w.g);
  const maxp = Math.max(0, Math.ceil(groups.length / w.n) - 1);
  w.p = Math.min(w.p || 0, maxp);
  const page = groups.slice(w.p * w.n, w.p * w.n + w.n);
  let html = '';
  page.forEach(function(g, gi) {
    const ggi = w.p * w.n + gi;
    html += groupCard(wi, g, ggi);
    if (w.openGroup === ggi) {
      const grows = g.rows.slice(0, 20);
      html += grows.map(function(r, i) { return rowCard(wi, r, 'g' + ggi + 'r' + i); }).join('');
      if (g.rows.length > grows.length) html += '<div style="font-size:11px;opacity:.6">+' + (g.rows.length - grows.length) + ' more — filter to narrow</div>';
    }
  });
  box.innerHTML = head + (html || '<div style="font-size:12px;opacity:.6">no matches — clear the filter</div>');
  const info = document.getElementById('wi-' + wi);
  if (info) info.textContent = groups.length + ' groups · page ' + (w.p + 1) + '/' + Math.max(1, Math.ceil(groups.length / w.n));
}
function wToggleRow(wi, uid) {
  const w = window._widgets[wi];
  if (!w) return;
  uniStopLive();
  w.open = (w.open === uid) ? -1 : uid;
  renderWidgetCards(wi);
}
function wToggleGroup(wi, gi) {
  const w = window._widgets[wi];
  if (!w) return;
  uniStopLive();
  w.openGroup = (w.openGroup === gi) ? -1 : gi;
  renderWidgetCards(wi);
}
function wSet(wi, field, el) {
  const w = window._widgets[wi];
  if (!w) return;
  w[field] = field === 'n' ? (parseInt(el.value, 10) || 20) : el.value;
  w.p = 0; w.open = -1; w.openGroup = -1;
  if (field === 'q') { renderWidgetCards(wi); saveWidgetsSoon(); }
  else { saveWidgets(); renderWidgets(); }
}
function wTitle(wi, el) {
  const w = window._widgets[wi];
  if (w) { w.t = el.value.slice(0, 40); saveWidgetsSoon(); }
}
function wPage(wi, d) {
  const w = window._widgets[wi];
  if (!w) return;
  const maxp = Math.max(0, Math.ceil(widgetRows(w).length / w.n) - 1);
  w.p = Math.min(maxp, Math.max(0, (w.p || 0) + d));
  w.open = -1;
  renderWidgetCards(wi);
}
function wRemove(wi) {
  if (!window._widgets) return;
  window._widgets.splice(wi, 1);
  saveWidgets(); renderWidgets();
}
function addViewPreset(kind, btn) {
  const PRESETS = {
    all: {t: 'all', q: '', g: 'none', s: 'new', n: 20},
    project: {t: 'by project', q: '', g: 'project', s: 'new', n: 20},
    money: {t: 'money', q: 'money gate', g: 'project', s: 'new', n: 20},
    waiting: {t: 'waiting', q: 'is:waiting', g: 'project', s: 'new', n: 20}
  };
  if (!window._widgets) window._widgets = [];
  if (window._widgets.length >= 12) { alert('12 views max — remove one first'); return; }
  if (btn) { const o = btn.textContent; btn.textContent = '…'; btn.disabled = true;
    setTimeout(function() { btn.textContent = o; btn.disabled = false; }, 900); }
  window._widgets.push(cleanWidget(PRESETS[kind] || PRESETS.all));
  saveWidgets(); renderWidgets();
  setTimeout(function() {
    try {
      const wl = document.getElementById('widgets').lastChild;
      if (wl && wl.scrollIntoView) wl.scrollIntoView(false);
    } catch (e) {}
  }, 60);
}
function waitFor(track) {
  // waiting = your notes + pending money gates. tap a badge -> see them.
  if (!window._widgets || !window._widgets.length) window._widgets = [cleanWidget({t: 'waiting', q: 'is:waiting', g: 'project'})];
  const w = window._widgets[0];
  w.q = track ? ('is:waiting ' + track) : 'is:waiting';
  w.g = 'project'; w.p = 0; w.open = -1;
  saveWidgets(); renderWidgets();
  try { document.getElementById('widgets').scrollIntoView(); } catch (e) {}
}
function uniDetail(r, uid) {
  const safeTrack = String(r.track || 'e062').replace(/[^a-z0-9]/gi, '') || 'e062';
  let h = '<div class=cdetail onclick="event.stopPropagation()"><div>' + esc(r.full || r.detail) + '</div>';
  if (r.leg) {
    h += '<div class=rowbtns style="margin-top:6px"><a href="/api/leg/' + r.leg + '" target=_blank><button>full log</button></a> ' +
      '<button onclick="uniWatchLive(' + r.leg + ',\'' + uid + '\',this)">watch live</button></div>' +
      '<pre id="uni-live-' + uid + '" style="max-height:24vh;overflow-y:auto;font-size:11px"></pre>';
  }
  h += '<div class=act-reply><input id="u-' + uid + '" placeholder="talk to the ' + esc(safeTrack) + ' agent…" onclick="event.stopPropagation()">' +
    '<button onclick="sendUniNote(\'' + safeTrack + '\',\'' + uid + '\',this)">send</button></div>' +
    '<div style="font-size:11px;opacity:.6">reply = queued for the next leg on this project.</div></div>';
  return h;
}
async function sendUniNote(track, uid, btn) {
  const inp = document.getElementById('u-' + uid);
  const v = inp ? inp.value.trim() : '';
  if (!v) return;
  const okTracks = {e058: 1, e059: 1, e060: 1, e061: 1, e062: 1, runner: 1};
  const t = okTracks[track] ? track : 'e062';
  btn.textContent = '…';
  const r = await (await fetch('/api/note', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({track: t, message: v})})).json();
  if (r.ok) { btn.textContent = 'sent ✓'; load(); }
  else { btn.textContent = 'error'; alert(r.error || 'failed'); }
}
function uniStopLive() {
  try { if (window._unitimer) clearInterval(window._unitimer); } catch (e) {}
  window._unitimer = null;
}
async function uniWatchLive(leg, uid, btn) {
  uniStopLive();
  btn.textContent = 'watching ● (tap to stop)';
  btn.onclick = function(e) { e.stopPropagation(); uniStopLive(); btn.textContent = 'watch live'; btn.onclick = function(ev) { ev.stopPropagation(); uniWatchLive(leg, uid, btn); }; };
  const pull = async function() {
    try {
      const r = await (await fetch('/api/leg/' + leg)).json();
      const pre = document.getElementById('uni-live-' + uid);
      if (pre && r.ok) { pre.textContent = (r.log || '').slice(-3000); pre.scrollTop = pre.scrollHeight; }
    } catch (e) {}
  };
  await pull();
  window._unitimer = setInterval(pull, 5000);
}
/* ---- money + lists: cards and divs, zero tables ---- */
function renderGates(d) {
  const box = document.getElementById('gates');
  if (!box) return;
  const props = d.proposals || [];
  const pend = props.filter(function(p) { return p.status === 'pending'; });
  const done = props.filter(function(p) { return p.status !== 'pending'; }).slice(0, 5);
  let html = pend.map(function(p) {
    return '<div class=card><div class=chead><span class=ctrack>' + esc(p.track) + '</span>' +
    '<span>gate #' + p.id + '</span><span class=needbadge>waiting</span>' +
    '<span style="margin-left:auto;font-size:11px;opacity:.6">$' + p.usd + '</span></div>' +
    '<div class=cbeat>' + esc(p.action) + ' — ' + esc(p.reason) + '</div>' +
    '<div class=rowbtns style="margin-top:4px">' +
    '<button onclick="decide(' + p.id + ',\'approved\',this)">approve</button>' +
    '<button onclick="decide(' + p.id + ',\'rejected\',this)">reject</button></div></div>';
  }).join('');
  if (done.length) html += '<div style="font-size:12px;opacity:.6;margin-top:6px">decided: ' +
    done.map(function(p) { return '#' + p.id + ' ' + p.status; }).join(' · ') + '</div>';
  box.innerHTML = html || '<div style="font-size:12px;opacity:.6">no money gates — nothing needs your money tap</div>';
}
function renderLists(d) {
  const tr = document.getElementById('tr');
  if (tr) tr.innerHTML = (d.trials || []).map(function(t) {
    return '<div style="padding:3px 0;border-bottom:1px dotted var(--bd)"><b>' + esc(t.name) + '</b> · renews ' + esc(t.renews) + ' · $' + t.usd + ' — ' + esc(t.note) + '</div>';
  }).join('') || '<div style="opacity:.6">none active</div>';
  const ib = document.getElementById('i');
  if (ib) ib.innerHTML = (d.ideas || []).map(function(x) {
    return '<div style="padding:3px 0;border-bottom:1px dotted var(--bd)">' + esc(x) + '</div>';
  }).join('') || '<div style="opacity:.6">empty</div>';
  const dr = document.getElementById('dir');
  if (dr) dr.innerHTML = String(d.directives || '').split('\n').filter(function(x) { return x.trim(); }).map(function(x) {
    return '<div style="padding:3px 0;border-bottom:1px dotted var(--bd)">' + esc(x) + '</div>';
  }).join('');
}
/* ---- personas: same flow, per-role lens (SQL-over-flow views) ---- */
function paintPersonaSeg() {
  const m = window._persona || 'owner';
  document.querySelectorAll('#seg-persona button[data-v]').forEach(function(b) {
    b.classList.toggle('on', b.getAttribute('data-v') === m);
  });
}
function setPersona(v, btn) {
  window._persona = v;
  try { localStorage.setItem('e062-persona', v); } catch (e) {}
  if (!window._widgets || !window._widgets.length) window._widgets = defaultWidgets();
  const w = window._widgets[0];
  if (v === 'owner') { setReportSilent('simple'); w.q = ''; w.g = 'none'; }
  if (v === 'builder') { setReportSilent('both'); w.q = ''; w.g = 'session'; }
  if (v === 'money') { setReportSilent('simple'); w.q = 'money gate'; w.g = 'project'; }
  w.p = 0; w.open = -1;
  paintPersonaSeg(); saveWidgets(); load();
}
function setReportSilent(v) {
  window._report = v;
  try { paintReportSeg(); } catch (e) {}
  try {
    fetch('/api/prefs', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({report: v})});
  } catch (e) {}
}
/* ---- live: what the agent is doing RIGHT NOW (auto, no tap needed) ---- */
function renderLive(d) {
  const box = document.getElementById('live');
  if (!box) return;
  try { if (!window._persona) window._persona = localStorage.getItem('e062-persona') || 'owner'; } catch (e) {}
  try { paintPersonaSeg(); } catch (e) {}
  const r = (d && d.runner) || {};
  if (r.running && r.run_id) {
    box.style.display = '';
    const head = document.getElementById('live-head');
    if (head) head.textContent = '\u25cf LIVE run #' + r.run_id + (r.scope ? ' \u00b7 ' + r.scope : '') + (r.trigger ? ' \u00b7 ' + r.trigger : '') + (r.started ? ' \u00b7 ' + elapsedMin(r.started) : '');
    liveStart(r.run_id);
  } else {
    box.style.display = 'none';
    liveStop();
  }
}
async function liveStart(leg) {
  if (window._liveleg === leg && window._livetimer) return;
  liveStop();
  window._liveleg = leg;
  try {
    const rs = await (await fetch('/api/runstate')).json();
    if (rs && rs.live_session) {
      const head = document.getElementById('live-head');
      if (head && head.textContent.indexOf('ses ') < 0) head.textContent += ' \u00b7 ses ' + rs.live_session.replace(/,/g, ' +');
    }
  } catch (e) {}
  const pull = async function() {
    try {
      const r = await (await fetch('/api/leg/' + leg)).json();
      const pre = document.getElementById('live-tail');
      if (pre && r.ok) {
        const lines = String(r.log || '').split('\n');
        const stepLines = lines.filter(function(l) { return /^(\d+\. |[A-Z].{0,80}\||did:|next:|learned:)/.test(l.trim()); });
        const tail = stepLines.length ? stepLines.slice(-12).join('\n') : lines.slice(-12).join('\n');
        pre.textContent = tail;
        pre.scrollTop = pre.scrollHeight;
      }
    } catch (e) {}
  };
  pull();
  window._livetimer = setInterval(pull, 5000);
}
function liveStop() {
  try { if (window._livetimer) clearInterval(window._livetimer); } catch (e) {}
  window._livetimer = null; window._liveleg = null;
}
