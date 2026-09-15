/* tablelib/table.js — one client for every p4 table (U3: SQL inline).
   Zero config: reads spec+rows from #tl-data-{ns}. State persists per ns.
   Tap header = sort. Filters live in the thead. Page size next to pager. */
var TL = TL || {};
function tlState(ns) {
  if (!TL[ns]) {
    var el = document.getElementById('tl-data-' + ns);
    var d = el ? JSON.parse(el.textContent) : { cols: [], rows: [], total: 0 };
    var saved = {};
    try { saved = JSON.parse(localStorage['tl-' + ns] || '{}'); } catch (e) {}
    TL[ns] = { cols: d.cols || [], all: d.rows || [], total: d.total || 0,
      page: 1, per: saved.per || d.per || 10,
      sortKey: saved.sortKey || d.sortKey || null,
      sortDir: saved.sortDir || d.sortDir || 1,
      filters: saved.filters || {},
      presets: d.presets || [], suggestions: d.suggestions || [],
      layout: d.layout || null,
      rowClick: d.rowClick || null, uviews: [] };
    try { TL[ns].uviews = JSON.parse(localStorage['tl-uviews-' + ns] || '[]'); } catch (e) {}
    var m = location.hash.match(new RegExp('tl-' + ns + '=([^&]*)'));
    if (m && m[1]) {
      try { tlApplyState(ns, JSON.parse(decodeURIComponent(escape(atob(decodeURIComponent(m[1])))))); } catch (e) {}
    }
    try {
      if (localStorage['tl-density'] === 'full') document.body.classList.remove('simple');
      if (localStorage['tl-cards'] === '1') document.body.classList.add('tl-cards');
      else if (!localStorage['tl-cards'] && window.innerWidth && window.innerWidth < 600)
        document.body.classList.add('tl-cards');
    } catch (e) {}
  }
  return TL[ns];
}
function tlSave(ns) {
  var s = tlState(ns);
  try { localStorage['tl-' + ns] = JSON.stringify({ per: s.per, sortKey: s.sortKey, sortDir: s.sortDir, filters: s.filters }); } catch (e) {}
}
function tlVal(r, k) {
  var v = r[k];
  return (v === null || v === undefined) ? '' : v;
}
function tlFiltered(ns) {
  var s = tlState(ns), out = s.all.filter(function (r) {
    for (var k in s.filters) {
      var f = s.filters[k];
      if (f === '' || f == null) continue;
      var v = tlVal(r, k);
      if (typeof f === 'object') {
        if (f.lo !== '' && f.lo != null && !(+v >= +f.lo)) return false;
        if (f.hi !== '' && f.hi != null && !(+v <= +f.hi)) return false;
      } else if (typeof v === 'number') { if (!(v <= +f)) return false; }
      else if (String(v).toLowerCase().indexOf(String(f).toLowerCase()) < 0) return false;
    }
    return true;
  });
  if (s.sortKey) {
    var k = s.sortKey, d = s.sortDir;
    out.sort(function (a, b) {
      var x = tlVal(a, k), y = tlVal(b, k);
      return (x > y ? 1 : x < y ? -1 : 0) * d;
    });
  }
  return out;
}
function tlSparkArr(a) {
  var vs = a.filter(function (x) { return !isNaN(+x); }).map(Number);
  if (!vs.length) return '—';
  var lo = Math.min.apply(0, vs), hi = Math.max.apply(0, vs);
  var bars = '▁▂▃▄▅▆▇';
  if (hi === lo) return bars[3].repeat(vs.length);
  return vs.map(function (v) { return bars[Math.min(6, Math.floor((v - lo) / (hi - lo) * 6))]; }).join('');
}
function tlPolyArr(a) {
  var vs = a.filter(function (x) { return !isNaN(+x); }).map(Number);
  if (vs.length < 2) return '—';
  var lo = Math.min.apply(0, vs), hi = Math.max.apply(0, vs), rng = (hi - lo) || 1, w = 80, h = 20;
  var pts = vs.map(function (v, i) {
    return (i * w / (vs.length - 1)).toFixed(1) + ',' + (h - (v - lo) / rng * (h - 2) - 1).toFixed(1);
  }).join(' ');
  return '<svg width="80" height="20"><polyline points="' + pts + '" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>';
}
function tlFmt(v, fmt) {
  if (v === null || v === undefined || !fmt) return v;
  var m = fmt.match(/\{:([+]?)\.(\d+)f\}/);
  if (!m || isNaN(+v)) return v;
  var s = (+v).toFixed(+m[2]);
  return (m[1] === '+' && +v >= 0) ? '+' + s : s;
}
function tlCell(ns, r, c) {
  var s = TL[ns];
  var v = r[c.key];
  if (v === null || v === undefined) return '—';
  if (c.kind === 'pill') {
    var pill = r[c.pill_key];
    var b = (pill !== '' && pill !== null && pill !== undefined) ? ' <span class="tl-thin">thin n=' + pill + '</span>' : '';
    return tlFmt(v, c.fmt) + b;
  }
  if (c.kind === 'bar') {
    var sc = (s && s._scales && s._scales[c.key]) || [0, 1];
    var pct = Math.max(0, Math.min(100, (+v - sc[0]) / ((sc[1] - sc[0]) || 1) * 100));
    return '<span class="tl-bar"><span style="width:' + pct.toFixed(0) + '%"></span></span> ' + tlFmt(v, c.fmt);
  }
  if (c.kind === 'spark') return (v instanceof Array) ? tlSparkArr(v) : String(v);
  if (c.kind === 'poly') return (v instanceof Array) ? tlPolyArr(v) : String(v);
  if (c.kind === 'num') return tlFmt(v, c.fmt);
  return String(v);
}
function tlRender(ns) {
  var s = tlState(ns);
  var list = tlFiltered(ns);
  var pages = Math.max(1, Math.ceil(list.length / s.per));
  if (s.page > pages) s.page = pages; if (s.page < 1) s.page = 1;
  var rows = list.slice((s.page - 1) * s.per, s.page * s.per);
  s._scales = {};
  s.cols.forEach(function (c) {
    if (c.kind !== 'bar') return;
    var vs = s.all.map(function (r) { return +r[c.key]; }).filter(function (x) { return !isNaN(x); });
    s._scales[c.key] = vs.length ? [Math.min.apply(0, vs), Math.max.apply(0, vs)] : [0, 1];
  });
  var h = '<thead><tr>' + s.cols.map(function (c) {
    var arr = (s.sortKey === c.key) ? (s.sortDir === 1 ? ' &#9650;' : ' &#9660;') : '';
    if (c.kind === 'text' || c.kind === 'num' || c.kind === 'pill' || c.kind === 'bar')
      return '<th class="' + (c.cls || '') + ' tl-sort" onclick="tlSort(\'' + ns + '\',\'' + c.key + '\')">' + c.label + arr + '</th>';
    return '<th class="' + (c.cls || '') + '">' + c.label + '</th>';
  }).join('') + '</tr><tr>' + s.cols.map(function (c) {
    if (!c.ph) return '<td class="' + (c.cls || '') + '"></td>';
    if (c.kind === 'num' || c.kind === 'pill' || c.kind === 'bar') {
      var fr = s.filters[c.key] || {};
      if (typeof fr !== 'object') fr = {};
      var lo = (fr.lo != null ? String(fr.lo) : '').replace(/"/g, '&quot;');
      var hi = (fr.hi != null ? String(fr.hi) : '').replace(/"/g, '&quot;');
      return '<td class="' + (c.cls || '') + '">'
        + '<input id="tl-f-' + ns + '-' + c.key + '-lo" oninput="tlFilter(\'' + ns + '\',\'' + c.key + '\',this.value,\'lo\')" placeholder="\u2265 min" value="' + lo + '"> '
        + '<input id="tl-f-' + ns + '-' + c.key + '-hi" oninput="tlFilter(\'' + ns + '\',\'' + c.key + '\',this.value,\'hi\')" placeholder="\u2264 max" value="' + hi + '"></td>';
    }
    var fv = (s.filters[c.key] || '').toString().replace(/"/g, '&quot;');
    return '<td class="' + (c.cls || '') + '"><input id="tl-f-' + ns + '-' + c.key + '" oninput="tlFilter(\'' + ns + '\',\'' + c.key + '\',this.value)" placeholder="' + c.ph + '" value="' + fv + '"></td>';
  }).join('') + '</tr></thead><tbody>';
  rows.forEach(function (r) {
    var tr = '<tr>';
    if (s.rowClick) tr = '<tr onclick="' + s.rowClick[0] + '(\'' + String(r[s.rowClick[1]]).replace(/'/g, '') + '\')" style="cursor:pointer">';
    h += tr + s.cols.map(function (c) {
      var al = (c.kind === 'num' || c.kind === 'pill' || c.kind === 'bar') ? 'tl-n' : 'tl-t';
      return '<td data-l="' + c.label + '" class="' + (c.cls || '') + ' ' + al + '">' + tlCell(ns, r, c) + '</td>';
    }).join('') + '</tr>';
  });
  var t = document.getElementById('tl-' + ns);
  if (t) t.outerHTML = '<table id="tl-' + ns + '">' + h + '</tbody></table>';
  var p = document.getElementById('tl-pager-' + ns);
  var cnt = String(list.length) + ((s.total > s.all.length) ? ' of ' + s.total : '') + ' rows';
  if (p) p.innerHTML = 'Page <input id="tl-pg-' + ns + '" type="number" value="' + s.page
    + '" min="1" max="' + pages + '" style="width:3.5em" onchange="tlGoto(\'' + ns + '\',this.value)">/' + pages
    + ' \u00b7 ' + cnt + ' \u00b7 <input id="tl-per-' + ns + '" type="number" value="' + s.per
    + '" min="1" max="1000" style="width:4.5em" onchange="tlSetPer(\'' + ns + '\',this.value)"> per page '
    + '<button onclick="tlPage(\'' + ns + '\',-1)">\u2190 Prev</button> '
    + '<button onclick="tlPage(\'' + ns + '\',1)">Next \u2192</button>';
tlRenderViews(ns);
  tlRenderStats(ns);
  var cardsEl = document.getElementById('tl-cards-' + ns);
  var tEl = document.getElementById('tl-' + ns);
  if (tlIsCards() && cardsEl) { tlRenderCards(ns); }
  else {
    if (cardsEl) cardsEl.style.display = 'none';
    if (tEl && tEl.parentElement) tEl.parentElement.style.display = '';
  }
  tlSave(ns);
}
function tlSort(ns, k) {
  var s = tlState(ns);
  if (s.sortKey === k) s.sortDir = -s.sortDir;
  else { s.sortKey = k; s.sortDir = 1; }
  s.page = 1; tlRender(ns);
}
var _tlT = {};
function tlFilter(ns, k, v, edge) {
  var s = tlState(ns);
  if (edge) {
    var o = s.filters[k];
    if (typeof o !== 'object' || o === null) o = {};
    o[edge] = v;
    s.filters[k] = o;
  } else s.filters[k] = v;
  s.page = 1;
  clearTimeout(_tlT[ns]);
  _tlT[ns] = setTimeout(function () {
    tlRender(ns);
    var el = document.getElementById('tl-f-' + ns + '-' + k + (edge ? '-' + edge : ''));
    if (el) { el.focus(); try { el.setSelectionRange(el.value.length, el.value.length); } catch (e) {} }
  }, 350);
  tlSave(ns);
}
function tlPage(ns, d) { var s = tlState(ns); s.page += d; tlRender(ns); }
function tlGoto(ns, v) {
  var s = tlState(ns);
  var list = tlFiltered(ns);
  var pages = Math.max(1, Math.ceil(list.length / s.per));
  s.page = Math.min(pages, Math.max(1, +v || 1));
  tlRender(ns);
}
function tlSetPer(ns, v) {
  var s = tlState(ns);
  s.per = Math.min(1000, Math.max(1, +v || 10));
  s.page = 1;
  tlRender(ns);
}
function tlSnap(ns) {
  var s = tlState(ns);
  return { sortKey: s.sortKey, sortDir: s.sortDir, per: s.per, filters: s.filters,
    density: document.body.classList.contains('simple') ? 'simple' : 'full',
    cards: document.body.classList.contains('tl-cards') ? 1 : 0 };
}
function tlApplyState(ns, st) {
  var s = tlState(ns);
  if (!st) return;
  if (st.sortKey !== undefined) s.sortKey = st.sortKey;
  if (st.sortDir !== undefined) s.sortDir = st.sortDir;
  if (st.per !== undefined) s.per = st.per;
  if (st.filters !== undefined) s.filters = st.filters;
  if (st.density) { document.body.classList.toggle('simple', st.density === 'simple'); try { localStorage['tl-density'] = st.density; } catch (e) {} }
  if (st.cards !== undefined) { document.body.classList.toggle('tl-cards', !!st.cards); try { localStorage['tl-cards'] = st.cards ? '1' : '0'; } catch (e) {} }
  s.page = 1;
}
function tlApplyView(ns, i, isPreset) {
  var s = tlState(ns);
  var v = isPreset ? s.presets[i] : s.uviews[i];
  if (!v) return;
  tlApplyState(ns, v.state);
  tlRender(ns);
}
function tlSaveView(ns) {
  var s = tlState(ns);
  var name = prompt('view name:');
  if (!name) return;
  s.uviews.push({ name: name, state: tlSnap(ns) });
  try { localStorage['tl-uviews-' + ns] = JSON.stringify(s.uviews); } catch (e) {}
  tlRenderViews(ns);
}
function tlShare(ns) {
  var h = '#tl-' + ns + '=' + encodeURIComponent(btoa(unescape(encodeURIComponent(JSON.stringify(tlSnap(ns))))));
  var url = location.href.split('#')[0] + h;
  try { location.hash = h; } catch (e) {}
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).catch(function () { prompt('copy link:', url); });
  else prompt('copy link:', url);
}
function tlMore(ns, which) {
  var s = tlState(ns);
  if (which === 'pre') s._morePre = !s._morePre; else s._moreSug = !s._moreSug;
  if (which === 'pre') tlRenderViews(ns); else tlRenderStats(ns);
}
function tlChipCollapse(ns, which, items, btn) {
  var s = tlState(ns);
  var open = (which === 'pre') ? !!s._morePre : !!s._moreSug;
  var vis = open ? items : items.slice(0, 3);
  var h = vis.map(btn).join('');
  if (!open && items.length > 3) h += ' <button data-more="1">+' + (items.length - 3) + ' more</button>';
  return h;
}
function tlRenderViews(ns) {
  var s = tlState(ns);
  var pe = document.getElementById('tl-presets-' + ns);
  if (pe) {
    pe.innerHTML = tlChipCollapse(ns, 'pre', s.presets, function (v, i) {
      return '<button data-p="' + i + '">' + String(v.name).replace(/</g, '&lt;') + '</button>';
    });
    pe.querySelectorAll('button[data-p]').forEach(function (b) {
      b.onclick = function () { tlApplyView(ns, +b.dataset.p, 1); };
    });
    pe.querySelectorAll('button[data-more]').forEach(function (b) {
      b.onclick = function () { tlMore(ns, 'pre'); };
    });
  }
  var el = document.getElementById('tl-uviews-' + ns);
  if (!el) return;
  el.innerHTML = s.uviews.map(function (v, i) {
    return '<button data-i="' + i + '">' + v.name.replace(/</g, '&lt;') + '</button>';
  }).join('');
  el.querySelectorAll('button').forEach(function (b) {
    b.onclick = function () { tlApplyView(ns, +b.dataset.i, 0); };
  });
}
function tlRenderStats(ns) {
  var s = tlState(ns);
  var el = document.getElementById('tl-stats-' + ns);
  if (!el) return;
  var h = 'insights: ' + tlChipCollapse(ns, 'sug', s.suggestions, function (g, i) {
    return '<button data-i="' + i + '" title="' + String(g.detail || '').replace(/"/g, '&quot;') + '">💡 ' + String(g.title).replace(/</g, '&lt;') + '</button>';
  }) + ' <button data-ideas="1">✨ ideas</button>';
  el.innerHTML = h;
  el.querySelectorAll('button[data-i]').forEach(function (b) {
    b.onclick = function () { tlSuggestion(ns, +b.dataset.i); };
  });
  el.querySelectorAll('button[data-more]').forEach(function (b) {
    b.onclick = function () { tlMore(ns, 'sug'); };
  });
  var ib = el.querySelector('button[data-ideas]');
  if (ib) ib.onclick = function () { tlIdeas(ns); };
}
function tlSuggestion(ns, i) {
  var s = tlState(ns);
  if (!s.suggestions[i]) return;
  tlApplyState(ns, s.suggestions[i].state);
  tlRender(ns);
}
function tlIdeas(ns) {
  var s = tlState(ns);
  fetch('api/suggest', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cols: s.cols.map(function (c) { return c.key; }), rows: s.all.slice(0, 200) }) })
    .then(function (r) { return r.json(); })
    .then(function (d) { if (d && d.suggestions && d.suggestions.length) { s.suggestions = d.suggestions; tlRenderStats(ns); } })
    .catch(function () {});
}
function tlCompute(ns) {
  var s = tlState(ns);
  var op = document.getElementById('tl-cmp-op-' + ns).value;
  var ka = document.getElementById('tl-cmp-a-' + ns).value;
  var kb = document.getElementById('tl-cmp-b-' + ns).value;
  var names = { div: ka + '/' + kb, sub: ka + '−' + kb, add: ka + '+' + kb, pct: ka + '% of ' + kb };
  var key = 'calc' + s.cols.length;
  s.all.forEach(function (r) {
    var a = +r[ka], b = +r[kb], v = NaN;
    if (!isNaN(a) && !isNaN(b)) {
      if (op === 'div' && b) v = a / b;
      if (op === 'sub') v = a - b;
      if (op === 'add') v = a + b;
      if (op === 'pct' && b) v = a / b * 100;
    }
    r[key] = isNaN(v) ? null : Math.round(v * 100) / 100;
  });
  s.cols.push({ key: key, label: names[op] || (ka + op + kb), cls: '', kind: 'num', ph: '≤ max' });
  s.sortKey = key; s.sortDir = 1; s.page = 1;
  tlRender(ns);
}
function tlIsCards() { return document.body.classList.contains('tl-cards'); }
function tlRenderCards(ns) {
  var s = tlState(ns);
  var list = tlFiltered(ns);
  var pages = Math.max(1, Math.ceil(list.length / s.per));
  if (s.page > pages) s.page = pages; if (s.page < 1) s.page = 1;
  var rows = list.slice((s.page - 1) * s.per, s.page * s.per);
  var layout = s.layout || [s.cols.map(function (c) { return c.key; })];
  var byKey = {};
  s.cols.forEach(function (c) { byKey[c.key] = c; });
  var h = rows.map(function (r) {
    var click = s.rowClick ? ' onclick="' + s.rowClick[0] + '(\'' + String(r[s.rowClick[1]]).replace(/'/g, '') + '\')" style="cursor:pointer"' : '';
    var lrows = layout.map(function (group, gi) {
      var cells = group.map(function (k, ki) {
        var c = byKey[k];
        if (!c) return '';
        if (gi === 0 && ki === 0) return '<span class="tl-f tl-hero">' + tlCell(ns, r, c) + '</span>';
        return '<span class="tl-f"><i>' + c.label + '</i> ' + tlCell(ns, r, c) + '</span>';
      }).join('');
      return '<div class="tl-r">' + cells + '</div>';
    }).join('');
    return '<div class="tl-card"' + click + '>' + lrows + '</div>';
  }).join('');
  var el = document.getElementById('tl-cards-' + ns);
  if (el) { el.innerHTML = h; el.style.display = ''; }
  var t = document.getElementById('tl-' + ns);
  if (t && t.parentElement) t.parentElement.style.display = 'none';
}
function tlDensity(ns, v) {
  document.body.classList.toggle('simple', v === 'simple');
  try { localStorage['tl-density'] = v; } catch (e) {}
}
function tlCards(ns) {
  var on = document.body.classList.toggle('tl-cards');
  try { localStorage['tl-cards'] = on ? '1' : '0'; } catch (e) {}
}
