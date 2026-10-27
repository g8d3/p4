async function main(){
  const d = await (await fetch('data.json')).json();
  document.getElementById('gen').textContent = '· Updated ' + d.generated_utc;
  document.getElementById('gen2').textContent = d.generated_utc;
  document.getElementById('src').textContent = d.source;
  const tb = document.querySelector('#screen tbody');
  for (const [t, v] of Object.entries(d.tickers)) {
    const tr = document.createElement('tr');
    if (v.error) { tr.innerHTML = `<td><b>${t}</b></td><td colspan="5">error: ${v.error}</td>`; }
    else {
      const cls = v.verdict.startsWith('TRIGGER') ? 'trig' : v.verdict.startsWith('WATCH') ? 'watch' : 'wait';
      const day = v.red_day === null ? '—' : (v.red_day ? `🔴 ${v.day_chg_pct}%` : `🟢 +${v.day_chg_pct}%`);
      tr.innerHTML = `<td><b>${t}</b></td><td>$${v.price}<br><small>${v.price_date}</small></td>` +
        `<td><b>${v.weekly_rsi ?? '—'}</b></td><td><span class="badge ${cls}">${v.verdict}</span></td>` +
        `<td>${day}</td><td>${v.pos_52w_pct}%<br><small>$${v.lo_52w}–$${v.hi_52w}</small></td>`;
    }
    tb.appendChild(tr);
  }
  const hist = document.getElementById('hist');
  for (const [t, v] of Object.entries(d.tickers)) {
    const h = document.createElement('div');
    if (v.error || !v.rsi30_events.length) { h.innerHTML = `<h3>${t}</h3><p>No RSI&lt;30 events in 5y window.</p>`; }
    else {
      const rows = v.rsi30_events.map(e =>
        `<tr><td>${e.date}</td><td>${e.rsi}</td><td>$${e.price}</td><td>${e.fwd6m_pct ?? '—'}%</td><td>${e.fwd12m_pct ?? '—'}%</td></tr>`).join('');
      h.innerHTML = `<h3>${t} — ${v.rsi30_events.length} signals</h3>
        <table><thead><tr><th>Date</th><th>RSI</th><th>Price</th><th>+6mo</th><th>+12mo</th></tr></thead><tbody>${rows}</tbody></table>`;
    }
    hist.appendChild(h);
  }
  const go = () => {
    const cap = +document.getElementById('cap').value || 0;
    const ret = +document.getElementById('ret').value || 0;
    const cyc = +document.getElementById('cyc').value || 0;
    const per = cap * ret / 100, yr = per * cyc;
    const comp = cap * Math.pow(1 + ret/100, cyc);
    document.getElementById('out').innerHTML =
      `<b>$${per.toFixed(0)}</b> per cycle · <b>$${yr.toFixed(0)}</b>/yr simple · <b>$${comp.toFixed(0)}</b> compounded (${cyc} cycles). ` +
      (ret >= 4 ? '⚠️ 4%+/cycle on SPY/QQQ is guru math — halve it.' : '✓ realistic band.');
  };
  document.getElementById('go').onclick = go; go();
}
main();
