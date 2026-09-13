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
  document.getElementById('ts').textContent = new Date().toISOString().slice(11, 16) + 'Z';
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
    ((waitByTrack[t.track] || 0) ? '<span class=needbadge>\u25cf' + waitByTrack[t.track] + ' waiting</span>' : '') +
    (paused ? '<span class=pausedtag>paused</span>' : '') +
    '<span style="margin-left:auto;font-size:11px;opacity:.6">' + (open ? '▾ close' : '▸ history + message') + '</span></div>' +
    '<div class=cbeat>' + esc(t.beat ? (t.beat.ts + ' ' + t.beat.status + ' ' + fmtDetail(t.beat.note)) : '') + '</div>' +
    (t.url ? '<div style="font-size:12px"><a href="' + esc(t.url) + '" onclick="event.stopPropagation()">' + esc(t.url) + '</a></div>' : '') +
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
  document.getElementById('inbox').innerHTML = d.notes.map(n =>
    '<tr><td>' + esc(n.ts) + '</td><td>' + esc(n.track) + '</td><td>' + esc(n.message) + '</td></tr>').join('') || '<tr><td colspan=3>empty — write from a project card above</td></tr>';
  const hs = document.getElementById('help-sum');
  if (hs) hs.textContent = (d.notes || []).length ? (d.notes.length + ' notes waiting — tap to read') : 'notes — empty, write from a project card';
  const hd = document.getElementById('help-det');
  if (hd && !window._helpTouched) hd.open = (d.notes || []).length > 0;
  const wt = document.getElementById('waiting');
  if (wt) wt.textContent = waitTotal ? ('\u25cf ' + waitTotal + ' waiting') : '';
  document.getElementById('w').textContent =
    'treasury: spent $' + d.runway.spent.toFixed(2) + ' earned $' + d.runway.earned.toFixed(2) +
    ' left $' + d.runway.left.toFixed(2) + ' of $300';
  document.getElementById('p').innerHTML = d.proposals.map(p =>
    '<tr><td>' + p.id + '</td><td>' + esc(p.track) + '</td><td>' + p.usd + '</td>' +
    '<td>' + esc(p.action) + ' — ' + esc(p.reason) + '</td><td>' + p.status +
    (p.status === 'pending'
      ? ' <button onclick="decide(' + p.id + ',\'approved\',this)">approve</button>' +
        '<button onclick="decide(' + p.id + ',\'rejected\',this)">reject</button>' : '') +
    '</td></tr>').join('') || '<tr><td colspan=5>none</td></tr>';
  try { restoreUniCtrls(); } catch (e) {}
  window._act = buildActivity(d);
  try { window._unirows = buildUnified(d); renderUni(); } catch (e) {}
  document.getElementById('runs').innerHTML = window._act.map((a, i) =>
    '<tr class=act onclick="toggleAct(' + i + ',this)"><td>' + esc(a.time) + '</td><td>' + esc(a.track) + '</td><td>' + esc(a.kind) + '</td><td>' + esc(fmtDetail(a.detail)) + ' ' + ((window._report === 'simple' && String(a.detail||'').indexOf(' | ') >= 0) ? '<span style="opacity:.5">…</span>' : '') + '</td></tr>'
  ).join('') || '<tr><td colspan=4>no activity yet — press run fleet now</td></tr>';
  const leg = document.getElementById('leg');
  if (leg) leg.textContent = d.leg_tail || 'no log yet';
  document.getElementById('tr').innerHTML = d.trials.map(t =>
    '<tr><td>' + esc(t.name) + '</td><td>' + esc(t.renews) + '</td><td>' + t.usd + '</td><td>' + esc(t.note) + '</td></tr>').join('') || '<tr><td colspan=4>none</td></tr>';
  document.getElementById('i').innerHTML = d.ideas.map(x => '<tr><td>' + esc(x) + '</td></tr>').join('');
  document.getElementById('dir').innerHTML = d.directives.split('\n').filter(x => x.trim()).map(x => '<tr><td>' + esc(x) + '</td></tr>').join('');
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
    '<div style="font-size:12px;opacity:.8">' + esc(t.plan || '') + '</div>' +
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
  if (r.summary) bits.push(r.summary);
  return bits.length ? (owner + ' | tech: ' + bits.join(' · ')) : owner;
}
function buildActivity(d) {
  const act = [];
  (d.runs || []).forEach(r => act.push({t: actTs(r.started), time: r.started || '',
    track: r.scope === 'fleet' ? 'runner' : (r.scope || ''), kind: 'run #' + r.id + ' · ' + (r.status || ''),
    detail: runLine(r), full: runLine(r)}));
  (d.events || []).forEach(e => act.push({t: actTs(e.ts), time: e.ts, track: e.track,
    kind: e.kind, detail: e.summary, full: e.summary}));
  act.sort((a, b) => b.t - a.t);
  return act.slice(0, 40);
}
function toggleAct(i, tr) {
  const a = (window._act || [])[i];
  if (!a) return;
  const next = tr.nextSibling;
  if (next && next.className === 'adetail') { next.remove(); return; }
  tr.parentNode.querySelectorAll('tr.adetail').forEach(x => x.remove());
  const dtr = document.createElement('tr');
  dtr.className = 'adetail';
  const safeTrack = String(a.track || 'e062').replace(/[^a-z0-9]/gi, '') || 'e062';
  dtr.innerHTML = '<td colspan=4><div>' + esc(a.full || a.detail) + '</div>' +
    '<div class=act-reply><input id="a-' + i + '" placeholder="talk to the ' + esc(safeTrack) + ' agent…">' +
    '<button onclick="sendActNote(\'' + safeTrack + '\',' + i + ',this)">send</button></div>' +
    '<div style="font-size:11px;opacity:.6">reply = follow-up note about THIS session, read next leg (queue only). to run a project now, use its card above.</div></td>';
  tr.after(dtr);
  const inp = document.getElementById('a-' + i);
  if (inp) inp.onclick = e => e.stopPropagation();
}
async function sendActNote(track, i, btn) {
  const inp = document.getElementById('a-' + i);
  const v = inp ? inp.value.trim() : '';
  if (!v) return;
  const okTracks = {e058: 1, e059: 1, e060: 1, e061: 1, e062: 1, runner: 1};
  const t = okTracks[track] ? track : 'e062';
  const old = btn.textContent;
  btn.textContent = '…';
  const r = await (await fetch('/api/note', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({track: t, message: v})})).json();
  if (r.ok) { btn.textContent = 'sent ✓'; load(); }
  else { btn.textContent = 'error'; alert(r.error || 'failed'); }
  setTimeout(() => { btn.textContent = old; }, 2500);
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

/* ---- 0 · all: one generic view (group/filter/sort/pages + session drill-down) ---- */
function uniCtrls() {
  return {
    q: (document.getElementById('q-all') || {}).value || '',
    g: (document.getElementById('g-all') || {}).value || 'none',
    s: (document.getElementById('s-all') || {}).value || 'new',
    n: parseInt(((document.getElementById('n-all') || {}).value || '20'), 10) || 20
  };
}
function saveUniCtrls() {
  try { localStorage.setItem('e062-uni', JSON.stringify(Object.assign(uniCtrls(), {p: window._unipage || 0}))); } catch (e) {}
}
function restoreUniCtrls() {
  try {
    const u = JSON.parse(localStorage.getItem('e062-uni') || '{}');
    if (u.q !== undefined && document.getElementById('q-all') && document.activeElement !== document.getElementById('q-all')) document.getElementById('q-all').value = u.q;
    if (u.g && document.getElementById('g-all')) document.getElementById('g-all').value = u.g;
    if (u.s && document.getElementById('s-all')) document.getElementById('s-all').value = u.s;
    if (u.n && document.getElementById('n-all')) document.getElementById('n-all').value = String(u.n);
    window._unipage = u.p || 0;
  } catch (e) {}
}
function uniChanged() { window._unipage = 0; window._uniopen = -1; uniStopLive(); saveUniCtrls(); renderUni(); }
function uniPage(d) {
  const rows = uniFiltered().length;
  const n = uniCtrls().n;
  const maxp = Math.max(0, Math.ceil(rows / n) - 1);
  window._unipage = Math.min(maxp, Math.max(0, (window._unipage || 0) + d));
  window._uniopen = -1; uniStopLive(); saveUniCtrls(); renderUni();
}
function buildUnified(d) {
  const rows = [];
  (d.runs || []).forEach(r => {
    const track = r.scope === 'fleet' ? 'runner' : (r.scope || '');
    rows.push({t: actTs(r.started), time: r.started || '', track: track,
      kind: 'session', session: 'run #' + r.id,
      detail: runLine(r), full: runLine(r), leg: r.id});
  });
  (d.events || []).forEach(e => rows.push({t: actTs(e.ts), time: e.ts, track: e.track,
    kind: e.kind, session: '', detail: e.summary, full: e.summary, leg: null}));
  (d.notes || []).forEach(n => rows.push({t: actTs(n.ts), time: n.ts, track: n.track,
    kind: 'owner note', session: '', detail: n.message, full: n.message, leg: null}));
  (d.proposals || []).forEach(pr => rows.push({t: actTs(pr.ts), time: pr.ts, track: pr.track,
    kind: 'money gate #' + pr.id, session: '', detail: '#' + pr.id + ' $' + pr.usd + ' ' + pr.action + ' \u2014 ' + pr.reason + ' (' + pr.status + ')',
    full: '#' + pr.id + ' $' + pr.usd + ' ' + pr.action + ' \u2014 ' + pr.reason + ' (' + pr.status + ')', leg: null}));
  return rows;
}
function uniFiltered() {
  const c = uniCtrls();
  const q = (c.q || '').toLowerCase();
  let rows = (window._unirows || []).slice();
  if (q) rows = rows.filter(r => ((r.track || '') + ' ' + (r.kind || '') + ' ' + (r.session || '') + ' ' + (r.detail || '')).toLowerCase().indexOf(q) >= 0);
  rows.sort((a, b) => c.s === 'old' ? (a.t - b.t) : (b.t - a.t));
  return rows;
}
function uniGroupKey(r, g) {
  if (g === 'project') return r.track || '?';
  if (g === 'session') return r.session || r.kind || '?';
  if (g === 'kind') return r.kind || '?';
  return '';
}
function renderUni() {
  const box = document.getElementById('uni');
  if (!box) return;
  const c = uniCtrls();
  saveUniCtrls();
  const rows = uniFiltered();
  const n = c.n, p = window._unipage || 0;
  const page = rows.slice(p * n, p * n + n);
  window._unipage_rows = page;
  let html = '', lastG = null;
  page.forEach((r, i) => {
    const gk = uniGroupKey(r, c.g);
    if (c.g !== 'none' && gk !== lastG) { html += '<div style="font-size:11px;opacity:.6;margin:6px 0 2px"><b>' + esc(gk) + '</b></div>'; lastG = gk; }
    const open = window._uniopen === i;
    html += '<div class="card' + (open ? ' open' : '') + '" onclick="toggleUni(' + i + ')">' +
      '<div class=chead><span class=ctrack>' + esc(r.track) + '</span><span>' + esc(r.kind) + '</span>' +
      (r.session ? '<span style="opacity:.6">' + esc(r.session) + '</span>' : '') +
      '<span style="margin-left:auto;font-size:11px;opacity:.6">' + esc(r.time || '') + '</span></div>' +
      '<div class=cbeat>' + esc(fmtDetail(r.detail)) + '</div>' +
      (open ? uniDetail(r, i) : '') + '</div>';
  });
  box.innerHTML = html || '<div style="font-size:12px;opacity:.6">no matches \u2014 clear the filter</div>';
  const info = document.getElementById('uni-info');
  if (info) info.textContent = rows.length + ' rows \u00b7 page ' + (p + 1) + '/' + Math.max(1, Math.ceil(rows.length / n));
}
function uniDetail(r, i) {
  const safeTrack = String(r.track || 'e062').replace(/[^a-z0-9]/gi, '') || 'e062';
  let h = '<div class=cdetail onclick="event.stopPropagation()"><div>' + esc(r.full || r.detail) + '</div>';
  if (r.leg) {
    h += '<div class=rowbtns style="margin-top:6px"><a href="/api/leg/' + r.leg + '" target=_blank><button>full log</button></a> ' +
      '<button onclick="uniWatchLive(' + r.leg + ',' + i + ',this)">watch live</button></div>' +
      '<pre id="uni-live-' + i + '" style="max-height:24vh;overflow-y:auto;font-size:11px"></pre>';
  }
  h += '<div class=act-reply><input id="u-' + i + '" placeholder="talk to the ' + esc(safeTrack) + ' agent\u2026" onclick="event.stopPropagation()">' +
    '<button onclick="sendUniNote(\'' + safeTrack + '\',' + i + ',this)">send</button></div>' +
    '<div style="font-size:11px;opacity:.6">reply = queued for the next leg on this project.</div></div>';
  return h;
}
function toggleUni(i) {
  uniStopLive();
  window._uniopen = (window._uniopen === i) ? -1 : i;
  renderUni();
}
async function sendUniNote(track, i, btn) {
  const inp = document.getElementById('u-' + i);
  const v = inp ? inp.value.trim() : '';
  if (!v) return;
  const okTracks = {e058: 1, e059: 1, e060: 1, e061: 1, e062: 1, runner: 1};
  const t = okTracks[track] ? track : 'e062';
  btn.textContent = '\u2026';
  const r = await (await fetch('/api/note', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({track: t, message: v})})).json();
  if (r.ok) { btn.textContent = 'sent \u2713'; load(); }
  else { btn.textContent = 'error'; alert(r.error || 'failed'); }
}
function uniStopLive() {
  try { if (window._unitimer) clearInterval(window._unitimer); } catch (e) {}
  window._unitimer = null;
}
async function uniWatchLive(leg, i, btn) {
  uniStopLive();
  btn.textContent = 'watching \u25cf (tap to stop)';
  btn.onclick = function(e) { e.stopPropagation(); uniStopLive(); btn.textContent = 'watch live'; btn.onclick = function(ev) { ev.stopPropagation(); uniWatchLive(leg, i, btn); }; };
  const pull = async function() {
    try {
      const r = await (await fetch('/api/leg/' + leg)).json();
      const pre = document.getElementById('uni-live-' + i);
      if (pre && r.ok) { pre.textContent = (r.log || '').slice(-3000); pre.scrollTop = pre.scrollHeight; }
    } catch (e) {}
  };
  await pull();
  window._unitimer = setInterval(pull, 5000);
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
  const q = document.getElementById('q-all'), g = document.getElementById('g-all'), sl = document.getElementById('s-all');
  if (v === 'owner') { setReportSilent('simple'); if (g) g.value = 'none'; if (sl) sl.value = 'new'; if (q) q.value = ''; }
  if (v === 'builder') { setReportSilent('both'); if (g) g.value = 'session'; if (sl) sl.value = 'new'; }
  if (v === 'money') { setReportSilent('simple'); if (g) g.value = 'project'; if (q) q.value = 'money gate'; }
  window._unipage = 0; window._uniopen = -1;
  paintPersonaSeg(); saveUniCtrls(); load();
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
function liveStart(leg) {
  if (window._liveleg === leg && window._livetimer) return;
  liveStop();
  window._liveleg = leg;
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
