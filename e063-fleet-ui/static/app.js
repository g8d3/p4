// fleet v2 UI: Waiting default, patch render, SSE live. No widget builder.
let D = null; // last full state
const S = {view: 'waiting', q: '', open: null, pg: 0};
const PER = 30;
const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;');

function splitOT(s) {
  s = String(s || ''); const i = s.indexOf(' | ');
  return i < 0 ? {o: s, t: s} : {o: s.slice(0, i).trim(), t: s.slice(i + 3).trim()};
}
function fmt(s) {
  const m = (D && D.prefs && D.prefs.report) || 'simple', p = splitOT(s);
  if (m === 'tech') return p.t;
  if (m === 'both') return p.o === p.t ? p.o : p.o + ' | ' + p.t;
  return p.o;
}
function ago(t) {
  try {
    const d = new Date(String(t).replace(' ', 'T') + 'Z');
    if (isNaN(d)) return String(t || '');
    const p = n => (n < 10 ? '0' : '') + n;
    return p(d.getMonth() + 1) + '/' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  } catch (e) { return String(t || ''); }
}
function dur(r) {
  try {
    if (!r.started) return '';
    const t0 = new Date(r.started.replace(' ', 'T') + 'Z').getTime();
    const t1 = r.ended ? new Date(r.ended.replace(' ', 'T') + 'Z').getTime() : Date.now();
    const s = Math.max(0, Math.round((t1 - t0) / 1000));
    return s < 60 ? s + 's' : Math.floor(s / 60) + 'm ' + (s % 60) + 's';
  } catch (e) { return ''; }
}

// ---- data selectors
function waitItems() {
  const out = [];
  (D.notes || []).forEach(n => out.push({k: 'n', t: n.ts, track: n.track, text: n.message}));
  (D.proposals || []).filter(p => p.status === 'pending').forEach(p =>
    out.push({k: 'g', t: p.ts, track: p.track, text: '#' + p.id + ' $' + p.usd + ' ' + p.action + ' — ' + p.reason, id: p.id}));
  out.sort((a, b) => (b.t < a.t ? -1 : 1));
  return out;
}
function match(s) {
  const q = S.q.trim().toLowerCase();
  if (!q) return true;
  return s.toLowerCase().indexOf(q) >= 0;
}

// ---- views
function vWaiting() {
  const items = waitItems().filter(w => match(w.track + ' ' + w.text));
  if (!items.length) return '<div class=empty>✓ nothing waiting — inbox zero.<br>Tap Projects to steer, Money to review decided gates.</div>';
  return items.slice(0, PER).map(w => w.k === 'g'
    ? '<div class="card wait-gate"><div class=row1><span class=track>' + esc(w.track) + '</span><b>' + esc(w.text.split(' — ')[0]) + '</b><span class=meta>' + esc(ago(w.t)) + '</span></div>' +
      '<div class=beat>' + esc(fmt(w.text.split(' — ').slice(1).join(' — ') || w.text)) + '</div>' +
      '<div class=btns><button class=approve onclick="decide(' + w.id + ',\'approved\',this)">approve</button><button class=reject onclick="decide(' + w.id + ',\'rejected\',this)">reject</button></div></div>'
    : '<div class="card wait-note"><div class=row1><span class=track>' + esc(w.track) + '</span><span class=meta>your note · ' + esc(ago(w.t)) + '</span></div>' +
      '<div class=beat>' + esc(w.text) + '</div></div>').join('');
}
function projHist(track) {
  const items = [];
  (D.events || []).filter(e => e.track === track).forEach(e => items.push({t: e.ts, k: e.kind, x: e.summary}));
  (D.runs || []).filter(r => r.scope === track).forEach(r =>
    items.push({t: r.started || '', k: 'run #' + r.id + ' ' + (r.status || ''), x: ('Run #' + r.id + ' ' + (r.status || '') + ' in ' + dur(r) + (r.summary ? ' — ' + r.summary : '')), leg: r.id}));
  (D.notes || []).filter(n => n.track === track).forEach(n => items.push({t: n.ts, k: 'owner note', x: n.message}));
  items.sort((a, b) => (b.t < a.t ? -1 : 1));
  return items.slice(0, 12);
}
function vProjects() {
  const list = (D.tracks || []).filter(t => match(t.track + ' ' + t.label + ' ' + (t.focus || '') + ' ' + ((t.beat && t.beat.note) || '')));
  return list.map(t => {
    const open = S.open === 'p:' + t.track;
    const b = t.beat ? ago(t.beat.ts) + ' ' + t.beat.status + ' — ' + fmt(t.beat.note) : '—';
    return '<div class="card' + (open ? ' open' : '') + '">' +
    '<div class=row1 onclick="tog(\'p:' + t.track + '\')"><span class=track>' + esc(t.track) + '</span><span>' + esc(t.label) + '</span>' +
    '<span class="rung ' + (t.rung > 0 ? 'r1' : 'r0') + '">rung ' + t.rung + '</span>' +
    (t.paused ? '<span style="font-size:11px;color:var(--warn)">paused</span>' : '') +
    '<span style="margin-left:auto;font-size:11px;opacity:.6">' + (open ? '▾' : '▸') + '</span></div>' +
    '<div class=beat><span class=meta>last:</span> ' + esc(b) + '</div>' +
    (t.focus ? '<div class=focus><span class=meta>next:</span> ' + esc(t.focus) + '</div>' : '') +
    (t.url ? '<div class=meta>link: <a href="' + esc(t.url) + '">' + esc(t.url) + '</a></div>' : '') +
    '<div class=btns><button onclick="pause(\'' + t.track + '\',this)">' + (t.paused ? 'resume' : 'pause') + '</button>' +
    '<button onclick="runScope(\'' + t.track + '\',this)">run</button></div>' +
    (open ? '<div class=hist>' + (projHist(t.track).map(h =>
      '<div><b>' + esc(ago(h.t)) + '</b> [' + esc(h.k) + '] ' + esc(fmt(h.x)) +
      (h.leg ? ' <a href="/api/leg/' + h.leg + '" target=_blank>log</a>' : '') + '</div>').join('') || '<div>no history</div>') + '</div>' +
      '<div class=msg><input id="m-' + t.track + '" placeholder="message to the ' + esc(t.track) + ' agent…"></div>' +
      '<div class=btns><button onclick="sendQ(\'' + t.track + '\',this)">queue (next leg)</button><button class=go onclick="sendR(\'' + t.track + '\',this)">send + run now</button></div>' : '') +
    '</div>';
  }).join('') || '<div class=empty>no projects match.</div>';
}
function vSessions() {
  const rows = (D.runs || []).filter(r => match('run #' + r.id + ' ' + (r.scope || '') + ' ' + (r.session || '') + ' ' + (r.summary || '')));
  return rows.slice(0, PER).map(r => {
    const open = S.open === 's:' + r.id;
    const bits = [];
    if (r.tokens != null) bits.push(Number(r.tokens).toLocaleString() + ' tok');
    if (r.cost_usd != null) bits.push('$' + Number(r.cost_usd).toFixed(4));
    if (r.session) bits.push('ses ' + r.session);
    return '<div class="card' + (open ? ' open' : '') + '"><div class=row1 onclick="tog(\'s:' + r.id + '\')">' +
    '<span class=dot ' + (r.status === 'done' ? 'ok' : (r.status === 'failed' ? 'bad' : '')) + '></span>' +
    '<b>run #' + r.id + '</b><span class=track>' + esc(r.scope || '') + '</span><span>' + esc(r.status || '') + '</span>' +
    '<span class=meta>' + esc(ago(r.started)) + ' · ' + esc(dur(r)) + '</span>' +
    '<span style="margin-left:auto;font-size:11px;opacity:.6">' + (open ? '▾' : '▸') + '</span></div>' +
    '<div class=beat>' + esc(fmt(r.summary || bits.join(' · ') || '—')) + '</div>' +
    (open ? '<div class=meta>' + esc(bits.join(' · ') + ' · ' + (r.trigger || '')) + ' <a href="/api/leg/' + r.id + '" target=_blank>full log</a></div>' +
      '<div class=log id="log-' + r.id + '">tap full log ↑</div>' : '') + '</div>';
  }).join('') || '<div class=empty>no sessions match.</div>';
}
function oneLine(s, n) {
  s = String(s == null ? '' : s).replace(/^-\s*/, '').trim();
  if (!s) return '—';
  return s.length > n ? s.slice(0, n) + '…' : s;
}
function firstRule() {
  const ls = String((D.directives || '')).split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'));
  return oneLine(ls[0] || 'no standing orders', 70);
}
function vMoney() {
  const w = D.runway, pct = Math.max(0, Math.min(100, 100 * (1 - w.left / 300)));
  const pend = (D.proposals || []).filter(p => p.status === 'pending' && match(p.track + ' ' + p.action));
  const done = (D.proposals || []).filter(p => p.status !== 'pending').slice(0, 8);
  return '<div class=card><div class=treasury><b>treasury</b><span>spent $' + w.spent.toFixed(2) + ' · earned $' + w.earned.toFixed(2) + ' · <b>left $' + w.left.toFixed(2) + '</b> of $300</span></div>' +
    '<div class=bar><i style="width:' + pct + '%"></i></div></div>' +
    (pend.map(p => '<div class="card wait-gate"><div class=row1><span class=track>' + esc(p.track) + '</span><b>gate #' + p.id + ' · $' + esc(p.usd) + '</b><span class=meta>' + esc(ago(p.ts)) + '</span></div>' +
      '<div class=beat>' + esc(p.action) + ' — ' + esc(fmt(p.reason)) + '</div>' +
      '<div class=btns><button class=approve onclick="decide(' + p.id + ',\'approved\',this)">approve</button><button class=reject onclick="decide(' + p.id + ',\'rejected\',this)">reject</button></div></div>').join('') || '<div class=empty>no pending gates.</div>') +
    (done.length ? '<div class=meta style="margin:8px 0">decided</div>' + done.map(p =>
      '<div class=card><div class=row1><span class=track>' + esc(p.track) + '</span><span>#' + p.id + ' $' + esc(p.usd) + ' ' + esc(p.action) + '</span><b>' + esc(p.status) + '</b></div></div>').join('') : '') +
    '<details><summary>trials (' + (D.trials || []).length + ') — ' + esc((D.trials || []).length ? ('next ' + oneLine((D.trials[0] || {}).name, 24) + ' $' + esc((D.trials[0] || {}).usd)) : 'none due') + '</summary><div>' + ((D.trials || []).map(t =>
      '<div class=card>' + esc(t.name) + ' renews ' + esc(t.renews) + ' $' + esc(t.usd) + ' ' + esc(t.note || '') + '</div>').join('') || 'none') + '</div></details>' +
    '<details><summary>standing orders — ' + esc(firstRule()) + '</summary><div class=log>' + esc(D.directives || '') + '</div></details>' +
    '<details><summary>ideas (' + (D.ideas || []).length + ')' + ((D.ideas || []).length ? ' — ' + esc(oneLine(D.ideas[0], 60)) : ' — none yet') + '</summary><div class=log>' + esc((D.ideas || []).join('\n')) + '</div></details>' +
    settingsHTML();
}
function settingsHTML() {
  const p = (D.prefs || {});
  return '<div class=card><b>display</b>' +
  '<div class=setrow>detail: <span class=seg>' + ['simple', 'both', 'tech'].map(m =>
    '<button class="' + (p.report === m ? 'on' : '') + '" onclick="setPref(\'report\',\'' + m + '\')">' + m + '</button>').join('') + '</span>' +
  'density: <span class=seg>' + ['comfortable', 'compact'].map(m =>
    '<button class="' + (p.density === m ? 'on' : '') + '" onclick="setPref(\'density\',\'' + m + '\')">' + m.slice(0, 4) + '</button>').join('') + '</span></div>' +
  '<div class=setrow>font <input type=range min=12 max=20 value="' + (p.font || 15) + '" onchange="setPref(\'font\',' + 'this.value)"><span>' + (p.font || 15) + 'px</span></div></div>';
}

// ---- render (preserve focus/scroll/drafts)
function saveFocus() {
  const a = document.activeElement;
  return a && a.id ? {id: a.id, v: a.value, s: (a.selectionStart || 0)} : null;
}
function restFocus(f) {
  if (!f) return;
  const el = document.getElementById(f.id);
  if (el && el.value !== undefined) { el.value = f.v || ''; try { el.setSelectionRange(f.s, f.s); } catch (e) {} if (document.activeElement !== el && f.v) el.focus(); }
}
function render() {
  if (!D) return;
  const f = saveFocus(), sy = window.scrollY;
  const n = waitItems().length;
  const tabs = [['waiting', 'Waiting' + (n ? ' (' + n + ')' : '')], ['projects', 'Projects'], ['sessions', 'Sessions'], ['money', 'Money']];
  document.getElementById('tabs').innerHTML = tabs.map(t =>
    '<button class="' + (S.view === t[0] ? 'on' : '') + '" onclick="go(\'' + t[0] + '\')">' + esc(t[1]) + (t[0] === 'waiting' && n ? '<span class=bdg>' + n + '</span>' : '') + '</button>').join('');
  document.getElementById('tabbar').innerHTML = tabs.map(t =>
    '<button class="' + (S.view === t[0] ? 'on' : '') + '" onclick="go(\'' + t[0] + '\')">' + esc(t[1]) + '</button>').join('');
  const m = document.getElementById('main');
  m.innerHTML = S.view === 'waiting' ? vWaiting() : S.view === 'projects' ? vProjects() : S.view === 'sessions' ? vSessions() : vMoney();
  const r = D.runner || {};
  document.getElementById('runstate').textContent = r.running ? ('● #' + (r.run_id || '?') + ' ' + (r.scope || '') + ' running') : (r.run_id ? ('○ last #' + r.run_id + ' ' + (r.status || '')) : '○ idle');
  document.getElementById('runbtn').disabled = !!r.running;
  applyPrefs(); renderAuth(); restFocus(f);
  window.scrollTo(0, sy);
}
function go(v) { S.view = v; S.open = null; render(); }
function tog(k) { S.open = S.open === k ? null : k; render(); }
function applyPrefs() {
  const p = D.prefs || {};
  document.documentElement.style.setProperty('--fs', (p.font || 15) + 'px');
  document.body.classList.toggle('compact', p.density === 'compact');
  try {
    const dark = localStorage.ft === 'd' || (localStorage.ft !== 'l' && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset.theme = dark ? 'dark' : '';
    if (!localStorage.ft) localStorage.ft = dark ? 'd' : 'l';
  } catch (e) {}
}
async function setPref(k, v) {
  if (k === 'font') v = parseInt(v, 10);
  D.prefs[k] = v; applyPrefs(); render();
  try { await fetch('/api/prefs', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({[k]: v})}); } catch (e) {}
}

// ---- actions (drafts ride along on every run — never drop owner words)
async function collectDrafts(scope) {
  const jobs = [];
  document.querySelectorAll('input[id^="m-"]').forEach(inp => {
    const t = inp.id.slice(2), v = (inp.value || '').trim();
    if (v && (scope === 'fleet' || t === scope)) jobs.push({track: t, message: v, inp});
  });
  for (const j of jobs) {
    try {
      const r = await (await fetch('/api/note', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({track: j.track, message: j.message})})).json();
      if (r.ok) j.inp.value = '';
    } catch (e) {}
  }
  return jobs.length;
}
async function post(path, body, btn, ok) {
  if (!D.me) { alert('login first — top right'); return; }
  const old = btn.textContent; btn.textContent = '…'; btn.disabled = true;
  try {
    const r = await (await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})).json();
    if (r.ok) { btn.textContent = ok || 'done ✓'; refresh(); }
    else { btn.textContent = 'error'; alert(r.error || 'failed'); }
  } catch (e) { btn.textContent = 'error'; alert(String(e)); }
  setTimeout(() => { btn.textContent = old; btn.disabled = false; }, 2000);
}
function runFleet(btn) { (async () => { const n = await collectDrafts('fleet'); post('/api/run', {scope: 'fleet'}, btn, n ? 'leg started with your messages ✓' : 'leg started ✓'); })(); }
function runScope(t, btn) { (async () => { const n = await collectDrafts(t); post('/api/run', {scope: t}, btn, n ? 'leg started with your message ✓' : 'leg started ✓'); })(); }
function pause(t, btn) {
  const paused = ((D.tracks || []).find(x => x.track === t) || {}).paused;
  post(paused ? '/api/resume' : '/api/pause', {track: t}, btn, paused ? 'resumed ✓' : 'paused ✓');
}
function sendQ(t, btn) {
  const v = (document.getElementById('m-' + t) || {}).value || '';
  if (!v.trim()) return;
  post('/api/note', {track: t, message: v.trim()}, btn, 'queued ✓');
}
function sendR(t, btn) {
  const inp = document.getElementById('m-' + t), v = ((inp || {}).value || '').trim();
  if (!v) { alert('write the message first'); return; }
  (async () => {
    btn.textContent = 'sending…'; btn.disabled = true;
    try {
      const r1 = await (await fetch('/api/note', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({track: t, message: v})})).json();
      if (!r1.ok) { alert(r1.error || 'note failed'); btn.disabled = false; return; }
      inp.value = '';
      const r2 = await (await fetch('/api/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({scope: t})})).json();
      if (r2.ok) refresh(); else alert((r2.error || 'run failed') + ' — message queued anyway');
    } catch (e) { alert(String(e)); }
    btn.disabled = false;
  })();
}
function decide(id, v, btn) {
  if (!D.me || D.me.role !== 'admin') { alert('admin only — login as admin to move money'); return; }
  post('/api/decide', {id, verdict: v}, btn, v + ' ✓');
}

// ---- auth
function renderAuth() {
  const box = document.getElementById('auth'), me = D.me;
  const key = me ? 'in:' + me.name : 'out' + (document.getElementById('au-n') ? ':t' : '');
  if (box.dataset.k === key) return;
  box.innerHTML = me ? '<b>' + esc(me.name) + '</b> <span style="opacity:.6">(' + esc(me.role) + ')</span><button onclick="logout()">logout</button><button onclick="theme()" title="dark/light">◐</button>'
    : '<input id=au-n placeholder=name style="width:70px"><input id=au-p type=password placeholder=password style="width:70px"><button onclick="login(this)">login</button><button onclick="register(this)">register</button><button onclick="theme()" title="dark/light">◐</button>';
  box.dataset.k = key;
}
function theme() {
  try { localStorage.ft = localStorage.ft === 'd' ? 'l' : 'd'; } catch (e) {}
  applyPrefs();
}
async function login(btn) {
  const n = document.getElementById('au-n'), p = document.getElementById('au-p');
  if (!n.value.trim() || !p.value) { alert('name + password first'); return; }
  btn.textContent = '…';
  const r = await (await fetch('/api/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: n.value.trim(), pw: p.value})})).json();
  if (r.ok) refresh(); else { alert(r.error || 'failed'); btn.textContent = 'login'; }
}
async function register(btn) {
  const n = document.getElementById('au-n'), p = document.getElementById('au-p');
  if (!n.value.trim() || !p.value) { alert('pick name + password (6+ chars)'); return; }
  const r = await (await fetch('/api/register', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: n.value.trim(), pw: p.value})})).json();
  if (r.ok) { alert(r.role === 'admin' ? 'registered as admin' : 'registered'); refresh(); } else alert(r.error || 'failed');
}
async function logout() { try { await fetch('/api/logout', {method: 'POST'}); } catch (e) {} refresh(); }

// ---- live
async function refresh() {
  try { D = await (await fetch('/api/state')).json(); render(); } catch (e) {}
  try {
    const v = await (await fetch('/api/version')).json();
    const el = document.getElementById('ver');
    if (el && v.ok) el.textContent = 'v' + v.running + (v.stale ? ' · updating…' : '');
  } catch (e) {}
}
function live() {
  const badge = () => document.getElementById('live');
  try {
    const es = new EventSource('/api/stream');
    es.onmessage = e => { try { const s = JSON.parse(e.data); if (s && typeof s === 'object') { if (!('me' in s) && D) s.me = D.me; D = s; } render(); } catch (err) {} };
    es.onopen = () => { const b = badge(); if (b) { b.textContent = '● LIVE'; b.className = 'on'; } };
    es.onerror = () => { const b = badge(); if (b) { b.textContent = '○ reconnecting'; b.className = 'off'; } };
  } catch (e) { setInterval(refresh, 15000); }
}
try { if (localStorage.ft === 'd') document.documentElement.dataset.theme = 'dark'; } catch (e) {}
refresh().then(live);
