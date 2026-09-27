/* Edge Terminal — admin/ops surface. Read-only except two explicit actions. */
'use strict';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; }, 3200);
  setTimeout(() => el.remove(), 3600);
}
async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `${path} → ${res.status}`);
  return data;
}
const when = (ts) => new Date(ts).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
const px = (v) => Number(v).toLocaleString('en-US', { maximumFractionDigits: 6 });

async function render() {
  const [st, led] = await Promise.all([api('/api/status'), api('/api/ledger?limit=100')]);
  document.title = `Edge Admin — ${st.mode}`;

  $('#a-mode').textContent = st.killed ? 'KILLED' : st.mode.toUpperCase();
  $('#a-mode').style.color = st.killed ? 'var(--down)' : '';
  $('#a-kill').hidden = !st.killed;
  $('#a-killbtn').textContent = st.killed ? 'Lift kill switch' : 'Engage kill switch';
  $('#a-killbtn').className = st.killed ? 'btn sm up' : 'btn sm down';

  const s = st.stats;
  const hitRate = s.hits + s.misses ? Math.round((s.hits / (s.hits + s.misses)) * 100) : 0;
  $('#a-stats').innerHTML = `
    <div class="stat"><div class="s-k">Uptime</div><div class="s-v">${Math.floor(st.uptimeSec / 60)}m ${st.uptimeSec % 60}s</div></div>
    <div class="stat"><div class="s-k">Requests</div><div class="s-v">${s.requests.toLocaleString()}</div></div>
    <div class="stat"><div class="s-k">Cache hit rate</div><div class="s-v">${hitRate}%</div></div>
    <div class="stat"><div class="s-k">Upstream errors</div><div class="s-v ${s.upstreamErr ? 'down' : 'up'}">${s.upstreamErr}</div></div>`;

  $('#a-up').innerHTML = `
    <div class="kv">
      <div class="k">Successful fetches</div><div class="v up">${s.upstreamOk}</div>
      <div class="k">Failed fetches</div><div class="v ${s.upstreamErr ? 'down' : ''}">${s.upstreamErr}</div>
      <div class="k">Last error</div><div class="v">${s.lastUpstreamErr ? s.lastUpstreamErr.error.slice(0, 44) : 'none'}</div>
      <div class="k">Last error at</div><div class="v">${s.lastUpstreamErr ? when(s.lastUpstreamErr.ts) : '—'}</div>
      <div class="k">Config edited</div><div class="v">${when(st.configMtime)}</div>
      <div class="k">Front-end version</div><div class="v">${st.version}</div>
    </div>`;

  $('#a-gates').innerHTML = `<div class="kv">
      <div class="k">Mode</div><div class="v">${st.mode}</div>
      <div class="k">Kill switch (data/STOP)</div><div class="v ${st.killed ? 'down' : 'up'}">${st.killed ? 'ENGAGED' : 'clear'}</div>
      <div class="k">HUMAN_GO (live money)</div><div class="v ${st.humanGo ? 'up' : 'down'}">${st.humanGo ? 'granted' : 'not granted'}</div>
      <div class="k">Signals logged</div><div class="v">${st.counts.signals}</div>
      <div class="k">Ledger rows</div><div class="v">${st.counts.ledger}</div>
    </div>
    <p class="hint" style="margin-top:9px">Live execution stays locked until <b>both</b> the paper ledger
    proves expectancy over ≥50 closed trades and a human writes <code>data/human_go.txt</code>.</p>`;

  $('#a-cache').innerHTML = st.cache.length
    ? st.cache.map((c) => `<tr><td>${c.key}</td><td class="num">${c.ageSec}</td><td class="num">${c.ttlSec}</td></tr>`).join('')
    : '<tr><td colspan="3" class="empty">cache is cold</td></tr>';

  const rows = led.rows.slice().reverse();
  $('#a-ledger-count').textContent = `(${rows.length} most recent of ${st.counts.ledger})`;
  $('#a-ledger').innerHTML = rows.length ? rows.map((r) => `
    <tr><td>${when(r.ts)}</td><td><span class="sig ${r.event === 'close' ? 'NEUTRAL' : 'LONG'}">${r.event}</span></td>
    <td>${r.coin || r.symbol || '—'}</td><td>${r.side || '—'}</td>
    <td class="num">${r.entry != null ? px(r.entry) : '—'}</td>
    <td class="num">${r.exit != null ? px(r.exit) : '—'}</td>
    <td class="num ${r.pnl > 0 ? 'up' : r.pnl < 0 ? 'down' : ''}">${r.pnl != null ? usd(r.pnl) : '—'}</td>
    <td class="num">${r.r != null ? r.r + 'R' : '—'}</td><td>${r.reason || r.event || ''}</td></tr>`).join('')
    : '<tr><td colspan="9" class="empty">no ledger rows yet — the app writes one per paper trade</td></tr>';

  const needs = st.needs;
  const items = [
    ...(needs.secrets || []).map((x) => [x.id, x.what + ' — ' + x.why, x.status]),
    ...((needs.human_gates || []).map((x) => [x.id, x.what + ' — ' + x.why, st.humanGo ? 'granted' : 'pending'])),
  ];
  $('#a-needs').innerHTML = items.length
    ? items.map((i) => `<tr><td>${i[0]}</td><td>${i[1]}</td><td>${i[2]}</td></tr>`).join('')
    : '<tr><td colspan="3" class="empty">needs.json has no pending items</td></tr>';
}

function bind() {
  $('#a-refresh').addEventListener('click', () => render().then(() => toast('refreshed', 'ok')).catch((e) => toast(e.message, 'err')));
  $('#a-reload').addEventListener('click', async () => {
    try { await api('/api/admin/reload', { method: 'POST' }); toast('config.json reloaded — no restart needed', 'ok'); render(); }
    catch (e) { toast(e.message, 'err'); }
  });
  $('#a-killbtn').addEventListener('click', async () => {
    try {
      const st = await api('/api/status');
      const path = st.killed ? '/api/admin/unkill' : '/api/admin/kill';
      await api(path, { method: 'POST' });
      toast(st.killed ? 'Kill switch lifted — board is live' : 'Kill switch engaged — board frozen', st.killed ? 'ok' : 'err');
      render();
    } catch (e) { toast(e.message, 'err'); }
  });
  setInterval(() => render().catch(() => {}), 10000);
}

document.addEventListener('DOMContentLoaded', () => { bind(); render().catch((e) => toast(e.message, 'err')); });
