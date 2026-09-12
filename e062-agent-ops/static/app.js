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
async function sendNoteSel(btn) {
  const t = document.getElementById('nt').value;
  const inp = document.getElementById('nm');
  const v = inp.value.trim();
  if (!v) return;
  const r = await (await fetch('/api/note', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({track: t, message: v})})).json();
  const c = document.getElementById('nconf');
  if (r.ok) { inp.value = ''; c.textContent = 'sent ✓ to ' + t; load(); }
  else { c.textContent = 'failed: ' + (r.error || '?'); }
  setTimeout(() => { c.textContent = ''; }, 4000);
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
    '<td>' + esc(t.plan) + '</td>' +
    '<td class=' + (t.beat && t.beat.status === 'blocked' ? 'blk' : '') + '>' +
      esc(t.beat ? t.beat.ts + ' ' + t.beat.status + ' ' + t.beat.note : '') + '</td>' +
    '<td>' + (t.url ? '<a href="' + esc(t.url) + '">' + esc(t.url) + '</a>' : '') + '</td>' +
    '<td class=rowbtns><button onclick="togPause(\'' + t.track + '\',this)">' +
      ((d.paused || []).includes(t.track) ? 'resume' : 'pause') + '</button></td></tr>'
  ).join('');
  document.getElementById('nt').innerHTML = d.tracks.map(t =>
    '<option value="' + t.track + '">' + t.track + '</option>').join('');
  document.getElementById('inbox').innerHTML = d.notes.map(n =>
    '<div><b>' + esc(n.ts) + ' [' + esc(n.track) + ']</b> ' + esc(n.message) + '</div>').join('') || '<div>empty — write the first note below</div>';
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
  const line = e => '<div>' + esc(e.ts) + ' [' + esc(e.track) + '/' + esc(e.kind) + '] ' + esc(e.summary) + '</div>';
  document.getElementById('e').innerHTML = d.events.map(line).join('') || '<div>none</div>';
  document.getElementById('tr').innerHTML = d.trials.map(t =>
    '<div>' + esc(t.name) + ' renews ' + esc(t.renews) + ' $' + t.usd + ' ' + esc(t.note) + '</div>').join('') || '<div>none</div>';
  document.getElementById('i').innerHTML = d.ideas.map(x => '<div>' + esc(x) + '</div>').join('');
  document.getElementById('dir').textContent = d.directives || '';
}
load();
setInterval(load, 60000);
