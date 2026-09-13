// Fleet board UI: three verbs — steer (pause/resume), help (notes), approve (money).
// All DOM writes happen inside functions. No top-level data references.
/* ---- accounts: register / login / logout (cookie session, money = admin) ---- */
function renderAuth() {
  const box = document.getElementById('auth');
  if (!box) return;
  const me = window._me;
  if (me) {
    box.innerHTML = '<b>' + esc(me.name) + '</b> <span style="opacity:.6">(' + esc(me.role) + ')</span> ' +
      '<button onclick="logout(this)">logout</button>';
  } else {
    box.innerHTML = '<input id=au-n placeholder="name" style="width:80px" aria-label="account name">' +
      '<input id=au-p type=password placeholder="password" style="width:80px" aria-label="password">' +
      '<button onclick="login(this)">login</button><button onclick="register(this)" title="first account becomes admin">register</button>';
  }
}
function authCreds() {
  const n = document.getElementById('au-n'), p = document.getElementById('au-p');
  return {name: (n && n.value || '').trim(), pw: (p && p.value || '')};
}
async function login(btn) {
  const c = authCreds();
  if (!c.name || !c.pw) { alert('name + password first'); return; }
  btn.textContent = '…';
  try {
    const r = await (await fetch('/api/login', {method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(c)})).json();
    if (r.ok) { window._me = {name: r.name, role: r.role}; renderAuth(); load(); }
    else { alert(r.error || 'login failed'); btn.textContent = 'login'; }
  } catch (e) { alert(String(e)); btn.textContent = 'login'; }
}
async function register(btn) {
  const c = authCreds();
  if (!c.name || !c.pw) { alert('pick a name + password (6+ chars) — first account becomes admin'); return; }
  btn.textContent = '…';
  try {
    const r = await (await fetch('/api/register', {method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(c)})).json();
    if (r.ok) {
      window._me = {name: r.name, role: r.role};
      renderAuth(); load();
      alert(r.role === 'admin' ? 'registered as admin — you can approve money gates' : 'registered — ask the admin to approve money moves');
    }
    else { alert(r.error || 'register failed'); btn.textContent = 'register'; }
  } catch (e) { alert(String(e)); btn.textContent = 'register'; }
}
async function logout() {
  try { await fetch('/api/logout', {method: 'POST'}); } catch (e) {}
  window._me = null;
  renderAuth(); load();
}
function needAuthOr(msg) {
  if (!window._me) { alert('login first — top right' + (msg ? ': ' + msg : '')); return true; }
  return false;
}

async function ctl(path, body, btn, okmsg) {
  if (needAuthOr()) return;
  if (path === '/api/decide' && (!window._me || window._me.role !== 'admin')) {
    alert('admin only — login as admin to move money');
    return;
  }
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
async function openCtl(path, body, btn, okmsg) {
  const old = btn.textContent;
  btn.textContent = '…'; btn.disabled = true;
  try {
    const r = await (await fetch(path, {method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)})).json();
    if (r.ok) { btn.textContent = okmsg || 'done ✓'; load(); }
    else { btn.textContent = 'error'; alert(r.error || 'failed'); if (/login required/i.test(r.error || '')) renderAuth(); }
  } catch (e) { btn.textContent = 'error'; alert(String(e)); }
  setTimeout(() => { btn.textContent = old; btn.disabled = false; }, 2500);
}
function togPause(t, btn) {
  const paused = (window._paused || []).includes(t);
  openCtl(paused ? '/api/resume' : '/api/pause', {track: t}, btn, paused ? 'resumed ✓' : 'paused ✓');
}
async function attachDrafts(scope) {
  // NEVER drop owner words: a Run tap carries any typed message with it.
  // Card boxes are n-<track>; row replies are u-<uid> with data-track.
  const jobs = [];
  document.querySelectorAll('input[id^="n-"]').forEach(function(inp) {
    const t = inp.id.slice(2);
    const v = (inp.value || '').trim();
    if (!v) return;
    if (scope !== 'fleet' && t !== scope) return;
    jobs.push({track: t, message: v, inp: inp});
  });
  document.querySelectorAll('input[id^="u-"]').forEach(function(inp) {
    const t = inp.getAttribute('data-track') || '';
    const v = (inp.value || '').trim();
    if (!v || !t) return;
    if (scope !== 'fleet' && t !== scope) return;
    jobs.push({track: t, message: v, inp: inp});
  });
  for (const j of jobs) {
    try {
      const r = await (await fetch('/api/note', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({track: j.track, message: j.message})})).json();
      if (r.ok) j.inp.value = '';
    } catch (e) {}
  }
  return jobs.length;
}
function runScope(t, btn) {
  (async function() {
    const n = await attachDrafts(t);
    openCtl('/api/run', {scope: t}, btn, n ? ('leg started with your message ✓') : 'leg started ✓');
  })();
}
function runFleet(btn) {
  (async function() {
    const n = await attachDrafts('fleet');
    openCtl('/api/run', {scope: 'fleet'}, btn, n ? ('fleet leg started with your messages ✓') : 'leg started ✓');
  })();
}
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
  try { window._me = (d.me && d.me.name) ? d.me : null; renderAuth(); } catch (e) {}
  try {
    const v = await (await fetch('/api/version')).json();
    const el = document.getElementById('ver');
    if (el && v.ok) el.textContent = 'v' + v.running + (v.stale ? ' STALE—restart' : '') + (v.dirty ? ' *' : '');
  } catch (e) {}
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
    (t.focus ? '<div style="font-size:12px"><span style="font-size:10px;opacity:.55">next:</span> ' + esc(t.focus) + '</div>' : '') +
    (t.url ? '<div style="font-size:12px"><span style="font-size:10px;opacity:.55">link:</span> <a href="' + esc(t.url) + '" onclick="event.stopPropagation()">' + esc(t.url) + '</a></div>' : '') +
    '<div class=rowbtns style="margin-top:6px" onclick="event.stopPropagation()">' +
    '<button onclick="togPause(\'' + t.track + '\',this)">' + (paused ? 'resume' : 'pause') + '</button> ' +
    '<button onclick="runScope(\'' + t.track + '\',this)" title="run now — anything you typed is attached automatically">run</button></div>' +
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
    '<div style="font-size:11px;opacity:.6">queue = read whenever the next leg runs. send + run now = your message starts a leg immediately on this project. plain run (above) also carries anything you typed.</div></div>';
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
    {t: 'projects', q: '', root: 'projects', n: 20},
    {t: 'sessions', q: '', root: 'sessions', n: 20},
    {t: 'waiting', q: 'is:waiting', root: 'waiting', n: 20}
  ];
}
function cleanWidget(w) {
  w = w || {};
  const root = ['projects', 'sessions', 'waiting'].indexOf(w.root) >= 0 ? w.root : 'projects';
  const d = rootDefaults(root);
  return {t: String(w.t || root).slice(0, 40), q: String(w.q || '').slice(0, 140),
    root: root,
    sortcol: String(w.sortcol || d.sortcol).slice(0, 12),
    sortdir: w.sortdir === 'asc' ? 'asc' : 'desc',
    reltab: ['sessions', 'notes', 'gates'].indexOf(w.reltab) >= 0 ? w.reltab : 'sessions',
    hide: (w.hide && typeof w.hide === 'object') ? w.hide : {},
    n: [10, 20, 50].indexOf(w.n) >= 0 ? w.n : 20,
    p: 0, open: -1, openRel: null};
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
    if (Array.isArray(w) && w.length <= 12 && (w.length === 0 || w[0].root)) { window._widgets = w.map(cleanWidget); return; }
  } catch (e) {}
  window._widgets = defaultWidgets().map(cleanWidget);
}
function slimWidgets() {
  return (window._widgets || []).map(function(w) { return {t: w.t, q: w.q, root: w.root, sortcol: w.sortcol, sortdir: w.sortdir, reltab: w.reltab, n: w.n, hide: w.hide || {}}; });
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
    else if (tok.indexOf('after:') === 0) { const d = Date.parse(tok.slice(6) + 'T00:00:00Z'); if (!isNaN(d)) rows = rows.filter(function(r) { return r.t >= d; }); }
    else if (tok.indexOf('before:') === 0) { const d = Date.parse(tok.slice(7) + 'T00:00:00Z'); if (!isNaN(d)) rows = rows.filter(function(r) { return r.t < d; }); }
    else rows = rows.filter(function(r) {
      return ((r.track || '') + ' ' + (r.kind || '') + ' ' + (r.session || '') + ' ' + (r.detail || '')).toLowerCase().indexOf(tok) >= 0;
    });
  });
  rows.sort(function(a, b) { return w.s === 'old' ? (a.t - b.t) : (b.t - a.t); });
  return rows;
}
var ALLCOLS = {
  projects: [['proj', 'PROJ'], ['rows', 'ROWS'], ['wait', 'WAIT'], ['latest', 'LATEST'], ['url', 'URL']],
  sessions: [['run', 'RUN'], ['ses', 'SES'], ['status', 'STATUS'], ['time', 'TIME']],
  waiting: [['item', 'ITEM'], ['proj', 'PROJ'], ['time', 'TIME'], ['go', 'GO']],
  relSessions: [['run', 'RUN'], ['ses', 'SES'], ['status', 'STATUS'], ['time', 'TIME']],
  relNotes: [['time', 'TIME'], ['note', 'NOTE']],
  relGates: [['gate', 'GATE'], ['usd', '$'], ['action', 'ACTION'], ['go', 'GO']],
  steps: [['time', 'TIME'], ['kind', 'KIND'], ['step', 'STEP']]
};
function visCols(w, table) {
  const hidden = (w.hide && w.hide[table]) || [];
  return ALLCOLS[table].filter(function(c) { return hidden.indexOf(c[0]) < 0; });
}
function wCol(wi, table, col, el) {
  const w = window._widgets[wi];
  if (!w) return;
  w.hide = w.hide || {};
  const h = w.hide[table] || (w.hide[table] = []);
  const i = h.indexOf(col);
  if (el.checked && i >= 0) h.splice(i, 1);
  if (!el.checked && i < 0) h.push(col);
  saveWidgets(); renderTable(wi);
}
function colPicker(wi, w) {
  // SELECT for the root table + its nested tables, one checkbox per column
  const tables = w.root === 'projects'
    ? [['projects', 'root'], ['relSessions', 'rel·sessions'], ['relNotes', 'rel·notes'], ['relGates', 'rel·gates'], ['steps', 'steps']]
    : (w.root === 'sessions' ? [['sessions', 'root'], ['steps', 'steps']] : [['waiting', 'root']]);
  window._colopen = window._colopen || {};
  const isopen = window._colopen[wi] ? ' open' : '';
  return '<details style="font-size:12px;margin:4px 0"' + isopen + ' ontoggle="try{window._colopen[' + wi + ']=this.open;}catch(e){}"><summary>columns (SQL SELECT)</summary><div>' +
    tables.map(function(t) {
      return '<div><span style="opacity:.6">' + t[1] + ':</span> ' + ALLCOLS[t[0]].map(function(c) {
        const on = visCols(w, t[0]).some(function(v) { return v[0] === c[0]; });
        return '<label style="margin-right:8px;white-space:nowrap"><input type=checkbox ' + (on ? 'checked' : '') +
          ' onchange="wCol(' + wi + ',\'' + t[0] + '\',\'' + c[0] + '\',this)"> ' + c[1] + '</label>';
      }).join('') + '</div>';
    }).join('') + '</div></details>';
}
function sqlCaption(w) {
  // the live SQL your taps build: SELECT cols FROM root WHERE … GROUP BY … ORDER BY … LIMIT … OFFSET …
  const from = {projects: 'projects', sessions: 'sessions', waiting: 'flow'}[w.root] || 'projects';
  const all = ALLCOLS[w.root] || ALLCOLS.projects;
  const vis = all.filter(function(c) { return ((w.hide && w.hide[w.root]) || []).indexOf(c[0]) < 0; }).map(function(c) { return c[0]; });
  const sel = vis.length === all.length ? '*' : (vis.join(', ') || '(none)');
  const toks = String(w.q || '').toLowerCase().split(/\s+/).filter(Boolean);
  const where = toks.map(function(t) {
    if (t === 'is:waiting') return 'wait > 0';
    if (t.indexOf('after:') === 0) return "time > '" + t.slice(6) + "'";
    if (t.indexOf('before:') === 0) return "time < '" + t.slice(7) + "'";
    return "text LIKE '%" + t + "%'";
  }).join(' AND ');
  return 'SELECT ' + sel + ' FROM ' + from + (where ? ' WHERE ' + where : '') +
    (w.root === 'projects' ? ' GROUP BY proj' : '') +
    ' ORDER BY ' + (w.sortcol || 'time') + ' ' + String(w.sortdir || 'desc').toUpperCase() +
    ' LIMIT ' + w.n + ' OFFSET ' + ((w.p || 0) * w.n);
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
  '<select onchange="wSet(' + wi + ',\'root\',this)" aria-label="root table">' + selOpts(wi, 'root', [['projects', 'table: projects'], ['sessions', 'table: sessions'], ['waiting', 'table: waiting']]) + '</select>' +

  '<select onchange="wSet(' + wi + ',\'n\',this)" aria-label="per page">' + selOpts(wi, 'n', [[10, '10/page'], [20, '20/page'], [50, '50/page']]) + '</select></div>' +
  '<div class=wlist id="wc-' + wi + '"></div>' +
  '<div class=rowbtns style="margin-top:6px;display:flex;gap:8px;align-items:center">' +
  '<button onclick="wPage(' + wi + ',-1)">‹ prev</button><span id="wi-' + wi + '" style="font-size:12px;opacity:.7"></span><button onclick="wPage(' + wi + ',1)">next ›</button></div></div>';
}
function renderWidgets() {
  const box = document.getElementById('widgets');
  if (!box || !window._widgets) return;
  if (!window._widgets.length) {
    box.innerHTML = '<div style="font-size:12px;opacity:.6">no views — add one above: +projects, +sessions or +waiting.</div>';
    return;
  }
  box.innerHTML = window._widgets.map(widgetHTML).join('');
  window._widgets.forEach(function(w, wi) { renderWidgetCards(wi); });
}
function renderTable(wi) {
  // tables-only refresh (filter typing keeps focus; controls untouched).
  // SQL caption + column picker live here so they stay in sync on every keystroke.
  const w = window._widgets[wi];
  const box = document.getElementById('wc-' + wi);
  if (!w || !box) return;
  const rows = widgetRows(w);
  let html = '<div style="font-size:11px;opacity:.6;margin-bottom:4px;font-family:monospace">SQL: ' +
    esc(sqlCaption(w)) + '</div>' + colPicker(wi, w) + waitBanner(w, rows);
  if (w.root === 'sessions') html += sesRoot(wi, w, rows);
  else if (w.root === 'waiting') html += waitRoot(wi, w, rows);
  else html += projRoot(wi, w, rows);
  box.innerHTML = html || '<div style="font-size:12px;opacity:.6">no matches — clear the filter</div>';
}
function wSet(wi, field, el) {
  const w = window._widgets[wi];
  if (!w) return;
  if (field === 'root') {
    w.root = el.value; const d = rootDefaults(w.root);
    w.sortcol = d.sortcol; w.sortdir = d.sortdir;
  } else if (field === 'n') w.n = parseInt(el.value, 10) || 20;
  else w[field] = el.value;
  w.p = 0; w.open = -1; w.openRel = null;
  if (field === 'q') { renderTable(wi); saveWidgetsSoon(); return; }
  saveWidgets(); renderWidgets();
}
function wTitle(wi, el) {
  const w = window._widgets[wi];
  if (w) { w.t = el.value.slice(0, 40); saveWidgetsSoon(); }
}
function wPage(wi, d) {
  const w = window._widgets[wi];
  if (!w) return;
  const rows = widgetRows(w);
  const total = w.root === 'projects' ? groupRows(rows, 'project').length : rows.filter(function(r) {
    return w.root === 'sessions' ? r.kind === 'session' : r.wait;
  }).length;
  const maxp = Math.max(0, Math.ceil(total / w.n) - 1);
  w.p = Math.min(maxp, Math.max(0, (w.p || 0) + d));
  w.open = -1; w.openRel = null;
  saveWidgets(); renderWidgets();
}
function wRemove(wi) {
  if (!window._widgets) return;
  window._widgets.splice(wi, 1);
  saveWidgets(); renderWidgets();
}
function addViewPreset(kind, btn) {
  const PRESETS = {
    projects: {t: 'projects', root: 'projects', n: 20},
    sessions: {t: 'sessions', root: 'sessions', n: 20},
    waiting: {t: 'waiting', root: 'waiting', n: 20}
  };
  if (!window._widgets) window._widgets = [];
  if (window._widgets.length >= 12) { alert('12 views max — remove one first'); return; }
  if (btn) { const o = btn.textContent; btn.textContent = '\u2026'; btn.disabled = true;
    setTimeout(function() { btn.textContent = o; btn.disabled = false; }, 900); }
  window._widgets.push(cleanWidget(PRESETS[kind] || PRESETS.projects));
  saveWidgets(); renderWidgets();
  setTimeout(function() {
    try {
      const wl = document.getElementById('widgets').lastChild;
      if (wl && wl.scrollIntoView) wl.scrollIntoView(false);
    } catch (e) {}
  }, 60);
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
  w.root = 'sessions';
  { const d = rootDefaults('sessions'); w.sortcol = d.sortcol; w.sortdir = d.sortdir; }
  w.q = q; w.p = 0; w.open = -1; w.openRel = null;
  saveWidgets(); renderWidgets();
}

function groupKey(r, g) {
  if (g === 'project') return r.track || '?';
  if (g === 'session') return r.session || r.kind || '?';
  if (g === 'kind') return r.kind || '?';
  return '';
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
function waitBanner(w, rows) {
  if (String(w.q || '').toLowerCase().indexOf('is:waiting') < 0) return '';
  return '<div style="border:1px solid #c0392b;border-radius:8px;padding:6px 8px;margin-bottom:6px;font-size:12px">' +
    '<b>\u26d4 ' + rows.length + ' need your tap.</b> Money gates: approve/reject below (money moves ONLY with your tap). ' +
    'Notes: your words to that project\u2019s agent, read on the next leg. Tap any \u25cf badge to come back here.</div>';
}
/* ---- nested tables: one root entity per view, relations unfold inline ---- */
function rootDefaults(root) {
  if (root === 'sessions') return {sortcol: 'time', sortdir: 'desc'};
  if (root === 'waiting') return {sortcol: 'time', sortdir: 'desc'};
  return {sortcol: 'latest', sortdir: 'desc'};
}
function trackUrl(key) {
  try {
    const t = ((window._board || {}).tracks || []).filter(function(x) { return x.track === key; })[0];
    return (t && t.url) || '';
  } catch (e) { return ''; }
}
function sortArrow(w, col) {
  return w.sortcol === col ? (w.sortdir === 'asc' ? ' \u25b2' : ' \u25bc') : '';
}
function cmpRows(a, b, col, dir) {
  let va, vb;
  if (col === 'run') { va = a.runid || 0; vb = b.runid || 0; }
  else if (col === 'status') { va = String((a.detail || '').match(/Run #\d+ (\w+)/) || ['', ''])[1]; vb = String((b.detail || '').match(/Run #\d+ (\w+)/) || ['', ''])[1]; }
  else { va = a.t || 0; vb = b.t || 0; }
  if (va < vb) return dir === 'asc' ? -1 : 1;
  if (va > vb) return dir === 'asc' ? 1 : -1;
  return 0;
}
function relCounts(rows, key) {
  const c = {sessions: 0, notes: 0, gates: 0};
  rows.forEach(function(r) {
    if (r.track !== key) return;
    if (r.kind === 'session') c.sessions++;
    else if (r.kind === 'owner note') c.notes++;
    else if (r.kind === 'money gate') c.gates++;
  });
  return c;
}
function clampCell(txt) {
  // long text fills 3 lines max; tap opens the rest — no more stretched rows
  return '<div class=clamp3 onclick="event.stopPropagation();this.classList.toggle(\'open\')">' + esc(txt) + '</div>';
}
function stepHead(w, oneKind) {
  const all = [['time', 'TIME'], ['kind', 'KIND'], ['step', 'STEP']];
  const vis = all.filter(function(c) {
    if (oneKind && c[0] === 'kind') return false;
    return ((w.hide && w.hide.steps) || []).indexOf(c[0]) < 0;
  });
  const suf = oneKind ? ' \u00b7 all ' + esc(oneKind) : '';
  return '<thead><tr>' + vis.map(function(c) { return '<th>' + c[1] + (c[0] === 'step' ? suf : '') + '</th>'; }).join('') + '</tr></thead>';
}
function stepRow(w, oneKind, s) {
  const cells = {
    time: '<td>' + esc(shortTime(s.time)) + '</td>',
    kind: '<td>' + esc(s.kind) + '</td>',
    step: '<td class=wrap>' + clampCell(s.detail) + '</td>'
  };
  const order = oneKind ? ['time', 'step'] : ['time', 'kind', 'step'];
  const hide = (w.hide && w.hide.steps) || [];
  return '<tr>' + order.filter(function(k) { return hide.indexOf(k) < 0; }).map(function(k) { return cells[k]; }).join('') + '</tr>';
}
function stepsOf(rows, runid) {
  const tag = '[run #' + runid + ']';
  return rows.filter(function(r) {
    return r.kind !== 'session' && String(r.detail || '').indexOf(tag) >= 0;
  }).sort(function(a, b) { return b.t - a.t; });
}
function renderWidgetCards(wi) {
  renderTable(wi);
}
function pagerInfo(wi, total, unit) {
  const w = window._widgets[wi];
  const info = document.getElementById('wi-' + wi);
  if (info) info.textContent = total + ' ' + unit + ' · page ' + ((w.p || 0) + 1) + '/' + Math.max(1, Math.ceil(total / w.n));
}
function wSort(wi, col) {
  const w = window._widgets[wi];
  if (!w) return;
  if (w.sortcol === col) w.sortdir = (w.sortdir === 'asc' ? 'desc' : 'asc');
  else { w.sortcol = col; w.sortdir = (col === 'proj' || col === 'status' || col === 'url') ? 'asc' : 'desc'; }
  w.p = 0;
  saveWidgets(); renderWidgets();
}
/* ---- root: PROJECTS (one row per project, relations unfold below) ---- */
function projRoot(wi, w, rows) {
  let groups = groupRows(rows, 'project');
  const dir = w.sortdir === 'asc' ? 1 : -1;
  groups.sort(function(a, b) {
    let va, vb;
    if (w.sortcol === 'proj') { va = a.key; vb = b.key; }
    else if (w.sortcol === 'url') { va = trackUrl(a.key); vb = trackUrl(b.key); }
    else if (w.sortcol === 'rows') { va = a.rows.length; vb = b.rows.length; }
    else if (w.sortcol === 'wait') { va = a.wait; vb = b.wait; }
    else { va = a.latest; vb = b.latest; }
    if (va < vb) return -dir; if (va > vb) return dir; return 0;
  });
  const maxp = Math.max(0, Math.ceil(groups.length / w.n) - 1);
  w.p = Math.min(w.p || 0, maxp);
  const page = groups.slice(w.p * w.n, w.p * w.n + w.n);
  w._groups = page;
  const cols = visCols(w, 'projects');
  const span = cols.length + 1;
  const cell = {
    proj: function(g) { return '<td><b>' + esc(g.key) + '</b></td>'; },
    rows: function(g) { return '<td>' + g.rows.length + '</td>'; },
    wait: function(g) { return '<td>' + (g.wait ? '<span class=needbadge>' + g.wait + '</span>' : '') + '</td>'; },
    latest: function(g) { return '<td>' + esc(shortTime(groupTime(g))) + '</td>'; },
    url: function(g) { const u = trackUrl(g.key); return '<td>' + (u ? '<a href="' + esc(u) + '" onclick="event.stopPropagation()">open</a>' : '') + '</td>'; }
  };
  const head = {proj: 'PROJ', rows: 'ROWS', wait: 'WAIT', latest: 'LATEST', url: 'URL'};
  let h = '<div class=rwrap><table class=rtable><thead><tr>' +
    cols.map(function(c) { return '<th onclick="wSort(' + wi + ',\'' + c[0] + '\')">' + head[c[0]] + sortArrow(w, c[0]) + '</th>'; }).join('') +
    '<th></th></tr></thead><tbody>';
  page.forEach(function(g, gi) {
    const open = w.openRel === g.key;
    h += '<tr class=prow onclick="wProjToggle(' + wi + ',' + gi + ')">' +
      cols.map(function(c) { return cell[c[0]](g); }).join('') +
      '<td>' + (open ? '\u25be' : '\u25b8') + '</td></tr>';
    if (open) {
      const rc = relCounts(window._unirows || [], g.key);
      if (rc.sessions + rc.notes + rc.gates === 0) {
        h += '<tr class=nrow><td colspan=' + span + '><div class=nwrap><table class=ntable><thead><tr><th>TIME</th><th>KIND</th><th>ROW</th></tr></thead><tbody>' +
          g.rows.slice(0, 20).map(function(r) { return '<tr><td>' + esc(shortTime(r.time)) + '</td><td>' + esc(r.kind) + '</td><td class=wrap>' + clampCell(r.detail) + '</td></tr>'; }).join('') +
          '</tbody></table></div></td></tr>';
      } else h += '<tr class=nrow><td colspan=' + span + '>' + relTabs(wi, w, g) + relTable(wi, w, g) + '</td></tr>';
    }
  });
  h += '</tbody></table></div>';
  setTimeout(function() { pagerInfo(wi, groups.length, 'projects'); }, 0);
  return h;
}
function wProjToggle(wi, gi) {
  const w = window._widgets[wi];
  if (!w || !w._groups || !w._groups[gi]) return;
  uniStopLive();
  const k = w._groups[gi].key;
  if (w.openRel === k) { w.openRel = null; renderTable(wi); return; }
  w.openRel = k;
  const all = window._unirows || [];
  const has = function(kind) { return all.some(function(r) { return r.track === k && r.kind === kind; }); };
  w.reltab = has('session') ? 'sessions' : (has('owner note') ? 'notes' : 'gates');
  renderTable(wi);
}
function relTabs(wi, w, g) {
  const c = relCounts(window._unirows || [], g.key);
  const tabs = [['sessions', 'Sessions (' + c.sessions + ')'], ['notes', 'Notes (' + c.notes + ')'], ['gates', 'Gates (' + c.gates + ')']];
  return '<div class=ntabs>' + tabs.map(function(t) {
    return '<button class="' + (w.reltab === t[0] ? 'on' : '') + '" onclick="event.stopPropagation();wRelTab(' + wi + ',\'' + t[0] + '\')">' + t[1] + '</button>';
  }).join('') + '</div>';
}
function wRelTab(wi, tab) {
  const w = window._widgets[wi];
  if (!w) return;
  w.reltab = tab;
  saveWidgets(); renderTable(wi);
}
function relTable(wi, w, g) {
  const tab = w.reltab || 'sessions';
  const mem = g.rows.filter(function(r) {
    if (tab === 'sessions') return r.kind === 'session';
    if (tab === 'notes') return r.kind === 'owner note';
    return r.kind === 'money gate';
  }).sort(function(a, b) { return b.t - a.t; }).slice(0, 20);
  if (!mem.length) return '<div style="font-size:12px;opacity:.6">no ' + tab + ' here</div>';
  let h;
  if (tab === 'sessions') {
    const rcols = visCols(w, 'relSessions');
    const rhead = {run: 'RUN', ses: 'SES', status: 'STATUS', time: 'TIME'};
    h = '<div class=nwrap><table class=ntable><thead><tr>' +
      rcols.map(function(c) { return '<th>' + rhead[c[0]] + '</th>'; }).join('') +
      '</tr></thead><tbody>';
    mem.forEach(function(r, i) {
      const uid = wi + ':rel:' + g.key + ':' + i;
      const st = String(r.detail || '').match(/Run #\d+ (\w+)/);
      const ses1 = String(r.sesid || '').split(',')[0];
      const rcell = {
        run: '<td><button onclick="event.stopPropagation();sesFilter(' + wi + ',\'run #' + r.runid + '\')">run #' + r.runid + '</button></td>',
        ses: '<td>' + (ses1 ? '<button onclick="event.stopPropagation();sesFilter(' + wi + ',\'ses ' + ses1 + '\')">ses ' + ses1 + '</button>' : '—') + '</td>',
        status: '<td>' + esc(st ? st[1] : '') + '</td>',
        time: '<td>' + esc(shortTime(r.time)) + '</td>'
      };
      h += '<tr onclick="wRowToggle(' + wi + ',\'' + uid + '\')">' +
        rcols.map(function(c) { return rcell[c[0]]; }).join('') + '</tr>';
      if (w.open === uid) h += '<tr class=drow><td colspan=' + rcols.length + '>' + uniDetail(r, uid) + '</td></tr>';
    });
    h += '</tbody></table></div>';
  } else if (tab === 'notes') {
    const ncols = visCols(w, 'relNotes');
    const nhead = {time: 'TIME', note: 'NOTE'};
    h = '<div class=nwrap><table class=ntable><thead><tr>' +
      ncols.map(function(c) { return '<th>' + nhead[c[0]] + '</th>'; }).join('') +
      '</tr></thead><tbody>';
    mem.forEach(function(r, i) {
      const uid = wi + ':note:' + g.key + ':' + i;
      const ncell = {
        time: '<td>' + esc(shortTime(r.time)) + '</td>',
        note: '<td class=wrap>' + clampCell(r.detail) + '</td>'
      };
      h += '<tr onclick="wRowToggle(' + wi + ',\'' + uid + '\')">' +
        ncols.map(function(c) { return ncell[c[0]]; }).join('') + '</tr>';
      if (w.open === uid) h += '<tr class=drow><td colspan=' + ncols.length + '>' + uniDetail(r, uid) + '</td></tr>';
    });
    h += '</tbody></table></div>';
  } else {
    const gcols = visCols(w, 'relGates');
    const ghead = {gate: 'GATE', usd: '$', action: 'ACTION', go: 'GO'};
    h = '<div class=nwrap><table class=ntable><thead><tr>' +
      gcols.map(function(c) { return '<th>' + ghead[c[0]] + '</th>'; }).join('') +
      '</tr></thead><tbody>';
    mem.forEach(function(r) {
      const gcell = {
        gate: '<td>#' + r.propId + '</td>',
        usd: '<td>' + esc(String(r.detail).match(/#\d+ \$([0-9.]+)/) ? String(r.detail).match(/#\d+ \$([0-9.]+)/)[1] : '') + '</td>',
        action: '<td class=wrap>' + clampCell(r.full || r.detail) + '</td>',
        go: '<td>' + (r.propPending
          ? '<button onclick="decide(' + r.propId + ',\'approved\',this)">approve</button> <button onclick="decide(' + r.propId + ',\'rejected\',this)">reject</button>'
          : esc(String(r.detail).match(/\((\w+)\)\s*$/) ? String(r.detail).match(/\((\w+)\)\s*$/)[1] : '')) + '</td>'
      };
      h += '<tr>' + gcols.map(function(c) { return gcell[c[0]]; }).join('') + '</tr>';
    });
    h += '</tbody></table></div>';
  }
  if (g.rows.length > mem.length && tab === 'sessions') h += '<div style="font-size:11px;opacity:.6">showing sessions only — other tabs hold the rest</div>';
  return h;
}
/* ---- root: SESSIONS (one row per run, steps unfold below) ---- */
function sesRoot(wi, w, rows) {
  let mem = rows.filter(function(r) { return r.kind === 'session'; });
  mem.sort(function(a, b) { return cmpRows(a, b, w.sortcol || 'time', w.sortdir || 'desc'); });
  const maxp = Math.max(0, Math.ceil(mem.length / w.n) - 1);
  w.p = Math.min(w.p || 0, maxp);
  const page = mem.slice(w.p * w.n, w.p * w.n + w.n);
  w._sespage = page;
  const scols = visCols(w, 'sessions');
  const shead = {run: 'RUN', ses: 'SES', status: 'STATUS', time: 'TIME'};
  const ssort = {run: 1, status: 1, time: 1};
  let h = '<div class=rwrap><table class=rtable><thead><tr>' +
    scols.map(function(c) { return ssort[c[0]]
      ? '<th onclick="wSort(' + wi + ',\'' + c[0] + '\')">' + shead[c[0]] + sortArrow(w, c[0]) + '</th>'
      : '<th>' + shead[c[0]] + '</th>'; }).join('') +
    '</tr></thead><tbody>';
  page.forEach(function(r, i) {
    const uid = wi + ':ses:' + (w.p * w.n + i);
    const st = String(r.detail || '').match(/Run #\d+ (\w+)/);
    const ses1 = String(r.sesid || '').split(',')[0];
    const extra = String(r.sesid || '').split(',').length - 1;
    const scell = {
      run: '<td><button onclick="event.stopPropagation();sesFilter(' + wi + ',\'run #' + r.runid + '\')">run #' + r.runid + '</button> <span style="opacity:.6">' + esc(r.track) + '</span></td>',
      ses: '<td>' + (ses1 ? '<button onclick="event.stopPropagation();sesFilter(' + wi + ',\'ses ' + ses1 + '\')">' + ses1 + '</button>' + (extra > 0 ? ' +' + extra : '') : '—') + '</td>',
      status: '<td>' + esc(st ? st[1] : '') + (r.wait ? ' <span class=needbadge>waiting</span>' : '') + '</td>',
      time: '<td>' + esc(shortTime(r.time)) + '</td>'
    };
    h += '<tr onclick="wRowToggle(' + wi + ',\'' + uid + '\')">' +
      scols.map(function(c) { return scell[c[0]]; }).join('') + '</tr>';
    if (w.open === uid) {
      const steps = stepsOf(window._unirows || [], r.runid).slice(0, 15);
      const kinds = {};
      steps.forEach(function(s) { kinds[s.kind] = 1; });
      const oneKind = Object.keys(kinds).length === 1 ? Object.keys(kinds)[0] : null;
      h += '<tr class=drow><td colspan=' + scols.length + '>' + (steps.length ? '<div class=nwrap><table class=ntable>' + stepHead(w, oneKind) + '<tbody>' +
          steps.map(function(s) { return stepRow(w, oneKind, s); }).join('') +
          '</tbody></table></div>' : '<div style="font-size:12px;opacity:.6">no tagged steps this run (older legs predate tags)</div>') +
        uniDetail(r, uid) + '</td></tr>';
    }
  });
  h += '</tbody></table></div>';
  setTimeout(function() { pagerInfo(wi, mem.length, 'sessions'); }, 0);
  return h;
}
/* ---- root: WAITING (everything that needs your tap) ---- */
function waitRoot(wi, w, rows) {
  let mem = rows.filter(function(r) { return r.wait; });
  mem.sort(function(a, b) { return b.t - a.t; });
  const maxp = Math.max(0, Math.ceil(mem.length / w.n) - 1);
  w.p = Math.min(w.p || 0, maxp);
  const page = mem.slice(w.p * w.n, w.p * w.n + w.n);
  const wcols = visCols(w, 'waiting');
  const whead = {item: 'ITEM', proj: 'PROJ', time: 'TIME', go: 'GO'};
  let h = '<div class=rwrap><table class=rtable><thead><tr>' +
    wcols.map(function(c) { return '<th>' + whead[c[0]] + '</th>'; }).join('') +
    '</tr></thead><tbody>';
  page.forEach(function(r, i) {
    const uid = wi + ':wait:' + (w.p * w.n + i);
    const item = r.kind === 'money gate' ? ('gate #' + r.propId) : r.kind;
    const go = r.propPending
      ? '<button onclick="decide(' + r.propId + ',\'approved\',this)">approve</button> <button onclick="decide(' + r.propId + ',\'rejected\',this)">reject</button>'
      : '<span style="opacity:.6">queued</span>';
    const wcell = {
      item: '<td><b>' + esc(item) + '</b></td>',
      proj: '<td>' + esc(r.track) + '</td>',
      time: '<td>' + esc(shortTime(r.time)) + '</td>',
      go: '<td>' + go + '</td>'
    };
    h += '<tr onclick="wRowToggle(' + wi + ',\'' + uid + '\')">' +
      wcols.map(function(c) { return wcell[c[0]]; }).join('') + '</tr>';
    if (w.open === uid) h += '<tr class=drow><td colspan=' + wcols.length + '>' + uniDetail(r, uid) + '</td></tr>';
  });
  h += '</tbody></table></div>';
  setTimeout(function() { pagerInfo(wi, mem.length, 'waiting'); }, 0);
  return h;
}
function wRowToggle(wi, uid) {
  const w = window._widgets[wi];
  if (!w) return;
  uniStopLive();
  w.open = (w.open === uid) ? -1 : uid;
  renderTable(wi);
}
function waitFor(track) {
  // waiting = your notes + pending money gates. tap a badge -> see them.
  if (!window._widgets || !window._widgets.length) window._widgets = [cleanWidget({t: 'waiting', root: 'waiting'})];
  const w = window._widgets[0];
  w.q = track ? ('is:waiting ' + track) : 'is:waiting';
  w.root = 'waiting'; w.p = 0; w.open = -1; w.openRel = null;
  saveWidgets(); renderWidgets();
  try { document.getElementById('widgets').scrollIntoView(); } catch (e) {}
}
function uniDetail(r, uid) {
  const safeTrack = String(r.track || 'e062').replace(/[^a-z0-9]/gi, '') || 'e062';
  let h = '<div class=cdetail onclick="event.stopPropagation()">' +
    ((r.wait && r.kind === 'owner note') ? '<div style="font-size:12px;margin-bottom:4px"><b>Your note</b> to the ' + esc(safeTrack) + ' agent \u2014 runs on the next leg. Add context below or leave it.</div>' : '') +
    '<div>' + esc(r.full || r.detail) + '</div>';
  if (r.leg) {
    h += '<div class=rowbtns style="margin-top:6px"><a href="/api/leg/' + r.leg + '" target=_blank><button>full log</button></a> ' +
      '<button onclick="uniWatchLive(' + r.leg + ',\'' + uid + '\',this)">watch live</button></div>' +
      '<pre id="uni-live-' + uid + '" style="font-size:11px;white-space:pre-wrap"></pre>';
  }
  h += '<div class=act-reply><input id="u-' + uid + '" data-track="' + safeTrack + '" placeholder="talk to the ' + esc(safeTrack) + ' agent…" onclick="event.stopPropagation()">' +
    '<button onclick="sendUniNote(\'' + safeTrack + '\',\'' + uid + '\',this)">queue</button> ' +
    '<button onclick="sendUniNoteRun(\'' + safeTrack + '\',\'' + uid + '\',this)">send + run now</button></div>' +
    '<div style="font-size:11px;opacity:.6">queue = read on the next leg. send + run now = starts a leg on this project immediately. plain run also carries your typed words.</div></div>';
  return h;
}
async function sendUniNoteRun(track, uid, btn) {
  const inp = document.getElementById('u-' + uid);
  const v = inp ? inp.value.trim() : '';
  if (!v) { alert('write the message first — or use plain run for no-message'); return; }
  const okTracks = {e058: 1, e059: 1, e060: 1, e061: 1, e062: 1, runner: 1};
  const t = okTracks[track] ? track : 'e062';
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
      if (pre && r.ok) {
        const t2 = String(r.log || '').split('\n').slice(-40).join('\n');
        if (pre.textContent !== t2) pre.textContent = t2;
      }
    } catch (e) {}
  };
  await pull();
  window._unitimer = setInterval(pull, 5000);
}
/* ---- money + lists: cards and divs, zero tables ---- */
function renderGates(d) {
  const box = document.getElementById('gates');
  if (!box) return;
  const ah = document.getElementById('authhint');
  if (ah) ah.innerHTML = window._me
    ? (window._me.role === 'admin' ? '' : 'logged in as viewer — only an admin can approve money. Ask the owner.')
    : 'to approve money: <b>register top-right</b> (first account becomes admin), then tap approve.';
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
  if (v === 'owner') { setReportSilent('simple'); w.q = ''; w.root = 'projects'; }
  if (v === 'builder') { setReportSilent('both'); w.q = ''; w.root = 'sessions'; }
  if (v === 'money') { setReportSilent('simple'); w.q = ''; w.root = 'waiting'; }
  { const d = rootDefaults(w.root); w.sortcol = d.sortcol; w.sortdir = d.sortdir; }
  w.p = 0; w.open = -1; w.openRel = null;
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
        const tail = (stepLines.length ? stepLines.slice(-12) : lines.slice(-12)).join('\n');
        if (pre.textContent !== tail) { pre.textContent = tail; }
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
