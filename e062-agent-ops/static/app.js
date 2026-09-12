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
function runScope(t, btn) { ctl('/api/run', {scope: t}, btn, 'leg started ✓'); }
function runFleet(btn) { ctl('/api/run', {scope: 'fleet'}, btn, 'leg started ✓'); }
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
async function sendNote(t, btn) {
  const inp = document.getElementById('n-' + t);
  const v = inp.value.trim();
  if (!v) return;
  const old = btn.textContent;
  btn.textContent = '…';
  const r = await (await fetch('/api/note', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({track: t, message: v})})).json();
  if (r.ok) { inp.value = ''; btn.textContent = 'sent ✓'; load(); }
  else { btn.textContent = 'error'; alert(r.error || 'failed'); }
  setTimeout(() => { btn.textContent = old; }, 2500);
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
  document.getElementById('ts').textContent = new Date().toISOString().slice(11, 16) + 'Z';
  document.getElementById('t').innerHTML = d.tracks.map(t =>
    '<tr><td class=c-track><b>' + esc(t.track) + '</b> ' + esc(t.label) + '</td>' +
    '<td class=' + (t.rung > 0 ? 'r1' : 'r0') + ' c-rung>' + t.rung + '</td>' +
    '<td class="c-plan ' + (window._wrap ? 'wrap' : 'nowrap') + '">' + esc(t.plan) + '</td>' +
    '<td class="' + (t.beat && t.beat.status === 'blocked' ? 'blk' : '') + ' c-beat ' + (window._wrap ? 'wrap' : 'nowrap') + '">' +
      esc(t.beat ? t.beat.ts + ' ' + t.beat.status + ' ' + t.beat.note : '') + '</td>' +
    '<td class="c-url ' + (window._wrap ? 'wrap' : 'nowrap') + '">' + (t.url ? '<a href="' + esc(t.url) + '">' + esc(t.url) + '</a>' : '') + '</td>' +
    '<td class="rowbtns c-ctrl"><input id="n-' + t.track + '" placeholder="note…" >' + '<br>' +
    '<button onclick="sendNote(\'' + t.track + '\',this)">send</button> ' +
    '<button onclick="togPause(\'' + t.track + '\',this)">' +
    ((d.paused || []).includes(t.track) ? 'resume' : 'pause') + '</button> ' +
    '<button onclick="runScope(\'' + t.track + '\',this)" title="start a runner leg focused on this track">run</button></td></tr>'
  ).join('');
  restoreDrafts(drafts);
  if (typing) { const el = document.getElementById(ae.id); if (el) { el.focus(); if (el.setSelectionRange && el.value) try { el.setSelectionRange(el.value.length, el.value.length); } catch (e) {} } }
  const rs = document.getElementById('runstate');
  if (rs) rs.innerHTML = runPill(d);
  document.getElementById('inbox').innerHTML = d.notes.map(n =>
    '<tr><td>' + esc(n.ts) + '</td><td>' + esc(n.track) + '</td><td>' + esc(n.message) + '</td></tr>').join('') || '<tr><td colspan=3>empty — write from a track row above</td></tr>';
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
  window._act = buildActivity(d);
  document.getElementById('runs').innerHTML = window._act.map((a, i) =>
    '<tr class=act onclick="toggleAct(' + i + ',this)"><td>' + esc(a.time) + '</td><td>' + esc(a.track) + '</td><td>' + esc(a.kind) + '</td><td>' + esc(a.detail) + '</td></tr>'
  ).join('') || '<tr><td colspan=4>no activity yet — press run fleet now</td></tr>';
  const leg = document.getElementById('leg');
  if (leg) leg.textContent = d.leg_tail || 'no log yet';
  document.getElementById('tr').innerHTML = d.trials.map(t =>
    '<tr><td>' + esc(t.name) + '</td><td>' + esc(t.renews) + '</td><td>' + t.usd + '</td><td>' + esc(t.note) + '</td></tr>').join('') || '<tr><td colspan=4>none</td></tr>';
  document.getElementById('i').innerHTML = d.ideas.map(x => '<tr><td>' + esc(x) + '</td></tr>').join('');
  document.getElementById('dir').innerHTML = d.directives.split('\n').filter(x => x.trim()).map(x => '<tr><td>' + esc(x) + '</td></tr>').join('');
}
function actTs(s) {
  try { return new Date(String(s).replace(' ', 'T') + 'Z').getTime(); } catch (e) { return 0; }
}
function runLine(r) {
  const bits = ['run #' + r.id + ' ' + (r.status || '')];
  const w = worked(r);
  if (w !== '—') bits.push(w);
  if (r.tokens != null) bits.push(Number(r.tokens).toLocaleString() + ' tok');
  if (r.tok_s != null) bits.push(r.tok_s + ' tok/s');
  if (r.cost_usd != null) bits.push('$' + Number(r.cost_usd).toFixed(4));
  if (r.scope) bits.push(r.scope + '/' + (r.trigger || ''));
  if (r.summary) bits.push(r.summary);
  return bits.join(' · ');
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
    '<div style="font-size:11px;opacity:.6">reply lands as a note to that track — the next leg reads it.</div></td>';
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
