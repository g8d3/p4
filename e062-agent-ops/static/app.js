// Fleet board UI: three verbs — steer (pause/resume), help (notes), approve (money).
// All DOM writes happen inside functions. No top-level data references.
function tok() {
  let t = localStorage.bt;
  if (!t) { t = prompt('board token — shown once in owner chat:'); if (t) localStorage.bt = t; }
  return t || '';
}
async function ctl(path, body, btn, okmsg) {
  const t = tok();
  if (!t) return;
  const old = btn.textContent;
  btn.textContent = '…'; btn.disabled = true;
  try {
    const r = await (await fetch(path, {method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Token': t},
      body: JSON.stringify(body)})).json();
    if (r.ok) { btn.textContent = okmsg || 'done ✓'; load(); }
    else { btn.textContent = 'error'; alert(r.error || 'failed'); }
  } catch (e) { btn.textContent = 'error'; alert(String(e)); }
  setTimeout(() => { btn.textContent = old; btn.disabled = false; }, 2500);
}
function togPause(t, btn) {
  const paused = (window._paused || []).includes(t);
  ctl(paused ? '/api/resume' : '/api/pause', {track: t}, btn, paused ? 'resumed ✓' : 'paused ✓');
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
  const d = await (await fetch('/api/board')).json();
  window._paused = d.paused || [];
  document.getElementById('ts').textContent = new Date().toISOString().slice(11, 16) + 'Z';
  document.getElementById('t').innerHTML = d.tracks.map(t =>
    '<tr><td><b>' + esc(t.track) + '</b> ' + esc(t.label) + '</td>' +
    '<td class=' + (t.rung > 0 ? 'r1' : 'r0') + '>' + t.rung + '</td>' +
    '<td class=plan>' + esc(t.plan) + '</td>' +
    '<td class=' + (t.beat && t.beat.status === 'blocked' ? 'blk' : '') + '>' +
      esc(t.beat ? t.beat.ts + ' ' + t.beat.status + ' ' + t.beat.note : '') + '</td>' +
    '<td>' + (t.url ? '<a href="' + esc(t.url) + '">' + esc(t.url) + '</a>' : '') + '</td>' +
    '<td class=rowbtns><input id="n-' + t.track + '" placeholder="note…" style=width:90px>' +
    '<button onclick="sendNote(\'' + t.track + '\',this)">send</button> ' +
    '<button onclick="togPause(\'' + t.track + '\',this)">' +
    ((d.paused || []).includes(t.track) ? 'resume' : 'pause') + '</button></td></tr>'
  ).join('');
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
  document.getElementById('e').innerHTML = d.events.map(e => '<tr><td>' + esc(e.ts) + '</td><td>' + esc(e.track) + '</td><td>' + esc(e.kind) + '</td><td>' + esc(e.summary) + '</td></tr>').join('') || '<tr><td colspan=4>none</td></tr>';
  document.getElementById('tr').innerHTML = d.trials.map(t =>
    '<tr><td>' + esc(t.name) + '</td><td>' + esc(t.renews) + '</td><td>' + t.usd + '</td><td>' + esc(t.note) + '</td></tr>').join('') || '<tr><td colspan=4>none</td></tr>';
  document.getElementById('i').innerHTML = d.ideas.map(x => '<tr><td>' + esc(x) + '</td></tr>').join('');
  document.getElementById('dir').innerHTML = d.directives.split('\n').filter(x => x.trim()).map(x => '<tr><td>' + esc(x) + '</td></tr>').join('');
}
async function applyPrefs() {
  try {
    const d = await (await fetch('/api/prefs')).json();
    const r = document.documentElement.style;
    r.setProperty('--fs', d.prefs.font + 'px');
    r.setProperty('--planw', d.prefs.planw + 'px');
    document.body.classList.toggle('compact', d.prefs.density === 'compact');
    document.getElementById('pf').value = d.prefs.font;
    document.getElementById('pw').value = d.prefs.planw;
    document.getElementById('pd').value = d.prefs.density;
    showTuneVals();
  } catch (e) {}
}
function showTuneVals() {
  document.getElementById('pfv').textContent = document.getElementById('pf').value + 'px';
  document.getElementById('pwv').textContent = document.getElementById('pw').value + 'px';
}
function previewTune() {
  const r = document.documentElement.style;
  r.setProperty('--fs', document.getElementById('pf').value + 'px');
  r.setProperty('--planw', document.getElementById('pw').value + 'px');
  document.body.classList.toggle('compact', document.getElementById('pd').value === 'compact');
  showTuneVals();
}
async function savePrefs(btn) {
  const t = tok();
  if (!t) return;
  btn.textContent = '…';
  const r = await (await fetch('/api/prefs', {method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-Token': t},
    body: JSON.stringify({font: document.getElementById('pf').value,
      planw: document.getElementById('pw').value,
      density: document.getElementById('pd').value})})).json();
  const s = document.getElementById('psaved');
  if (r.ok) { btn.textContent = 'save'; s.textContent = 'saved ✓'; }
  else { btn.textContent = 'save'; s.textContent = 'failed'; }
  setTimeout(() => { s.textContent = ''; }, 2500);
}
document.getElementById('pf').addEventListener('input', previewTune);
document.getElementById('pw').addEventListener('input', previewTune);
document.getElementById('pd').addEventListener('change', previewTune);
load();
applyPrefs();
setInterval(load, 60000);
