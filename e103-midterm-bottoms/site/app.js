"use strict";
/* Midterm bottoms page. Only input: midterms.json (same directory).
   No dependencies, no framework. */
var DATA_URL = "midterms.json";

var SVG_NS = "http://www.w3.org/2000/svg";

function el(tag, attrs, parent) {
  var n = document.createElementNS(SVG_NS, tag);
  if (attrs) {
    for (var k in attrs) {
      if (k === "text") { n.textContent = attrs[k]; }
      else { n.setAttribute(k, attrs[k]); }
    }
  }
  if (parent) { parent.appendChild(n); }
  return n;
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/* Null cell: em-dash with hover reason. Never blank, never zero-filled. */
function dash(reason) {
  return '<span class="dash" title="' + esc(reason || "Unknown: no source value") + '">—</span>';
}

function isNum(x) { return typeof x === "number" && isFinite(x); }

/* Stats arrive as percents (43.5) but accept fractions (0.435) too. */
function asPct(x) {
  if (!isNum(x)) { return null; }
  return x > 1 || x < -1 ? x : x * 100;
}

function fmtPct1(x) {
  var p = asPct(x);
  return p === null ? null : p.toFixed(1) + "%";
}

function fmtSigned1(x) {
  if (!isNum(x)) { return null; }
  return (x > 0 ? "+" : "") + x.toFixed(1) + "%";
}

function stanceColor(stance) {
  if (stance === "hiking") { return "#c0392b"; }
  if (stance === "cutting") { return "#1e8449"; }
  if (stance === "flat") { return "#7f8c8d"; }
  return null; /* unknown -> hollow */
}

/* ---------- (1) verdict: fully composed from stats, no hardcoded claim ---------- */
function composeVerdict(stats) {
  if (!stats || !isNum(stats.n) || stats.n === 0) {
    return "Not enough midterm data to judge whether stocks bottom around elections.";
  }
  var parts = [];
  var hit = asPct(stats.hit_rate_2m);
  var share = asPct(stats.share_relief_beats_fear);
  var medD = stats.median_depth;   /* negative drawdown, e.g. -11.75 */
  var medH = stats.median_height;  /* positive rally, e.g. +26.79 */
  var medBA = stats.median_ba;

  parts.push("Across " + stats.n + " midterms since 1934, ");
  if (hit === null) {
    parts.push("the timing of market bottoms is unmeasured");
  } else if (hit >= 50) {
    parts.push("a majority (" + hit.toFixed(1) + "%) bottomed within 2 months of Election Day, so bottoms cluster near the vote");
  } else {
    parts.push("only " + hit.toFixed(1) + "% bottomed within 2 months of Election Day, so bottoms do not tightly cluster on the vote");
  }
  parts.push("; ");

  var wk = stats.weekly;
  if (wk && isNum(wk.n) && wk.n > 0) {
    var h4 = asPct(wk.hit_4w), h8 = asPct(wk.hit_8w);
    parts.push("at weekly precision (" + wk.n + " midterms since 1970), " +
      (h4 === null ? "the 4-week hit rate is unmeasured" : h4.toFixed(1) + "% bottomed within 4 weeks") + " and " +
      (h8 === null ? "the 8-week hit rate is unmeasured" : h8.toFixed(1) + "% within 8 weeks"));
    if (isNum(wk.median_offset_days)) {
      var off = wk.median_offset_days;
      parts.push(", the median bottom landing " + Math.abs(Math.round(off)) + " days " +
        (off <= 0 ? "before" : "after") + " the vote");
    }
    parts.push("; ");
  }

  if (isNum(medD) && isNum(medH)) {
    var fearMag = Math.abs(medD);
    parts.push("the median fear drawdown was " + medD.toFixed(2) + "% and the median relief rally was +" +
      medH.toFixed(2) + "%, so the typical relief rally has " +
      (medH > fearMag ? "more than offset" : "not offset") + " the preceding fear leg");
    if (isNum(medBA)) {
      parts.push(" (median relief/fear ratio " + medBA.toFixed(2) + "x)");
    }
    parts.push(". ");
  } else {
    parts.push("median fear/relief legs are unmeasured. ");
  }

  if (share !== null) {
    parts.push("Relief beat fear in " + share.toFixed(1) + "% of measured cases" +
      (share >= 50 ? " — the usual pattern, not the exception. " : " — fear usually wins, contrary to the relief-rally story. "));
  }
  if (isNum(stats.median_ba_hiking) || isNum(stats.median_ba_cutting)) {
    var h = isNum(stats.median_ba_hiking) ? stats.median_ba_hiking.toFixed(2) + "x" : "unknown";
    var c = isNum(stats.median_ba_cutting) ? stats.median_ba_cutting.toFixed(2) + "x" : "unknown";
    parts.push("Median relief/fear ratio: " + h + " when hiking, " + c + " when cutting.");
  }
  return parts.join("").replace(/\s+/g, " ").trim();
}

/* ---------- (2) overlay chart ---------- */
function drawOverlay(svg, elections) {
  var W = 720, H = 420, L = 52, R = 14, T = 14, B = 34;
  var K0 = -12, K1 = 12;
  svg.innerHTML = "";
  var all = [];
  elections.forEach(function (e) {
    (e.path || []).forEach(function (p) { if (isNum(p.v)) { all.push(p.v); } });
  });
  if (!all.length) {
    el("text", { x: 20, y: 30, text: "No path data." }, svg);
    return;
  }
  var lo = Math.min.apply(null, all.concat([100]));
  var hi = Math.max.apply(null, all.concat([100]));
  var pad = (hi - lo) * 0.06 || 1;
  lo -= pad; hi += pad;
  function X(k) { return L + (k - K0) / (K1 - K0) * (W - L - R); }
  function Y(v) { return T + (1 - (v - lo) / (hi - lo)) * (H - T - B); }

  /* shaded bottom zone k in [-2,2] */
  el("rect", { x: X(-2), y: T, width: X(2) - X(-2), height: H - T - B, "class": "zone-rect" }, svg);

  /* gridlines */
  var ticks = 5, i, g;
  for (i = 0; i <= ticks; i++) {
    g = lo + (hi - lo) * i / ticks;
    el("line", { x1: L, y1: Y(g), x2: W - R, y2: Y(g), "class": "grid" }, svg);
    el("text", { x: 4, y: Y(g) + 4, text: Math.round(g) }, svg);
  }
  /* election-day vertical + 100 baseline */
  el("line", { x1: X(0), y1: T, x2: X(0), y2: H - B, "class": "grid" }, svg);
  el("line", { x1: L, y1: Y(100), x2: W - R, y2: Y(100), "class": "base100" }, svg);

  /* x labels */
  [["-12", -12], ["-6", -6], ["Election", 0], ["+6", 6], ["+12", 12]].forEach(function (t) {
    el("text", { x: X(t[1]) - (t[0].length > 3 ? 20 : 8), y: H - 12, text: t[0] + (t[1] === 0 ? "" : "m") }, svg);
  });
  el("text", { x: L, y: H - 1, text: "" }, svg);

  /* individual paths */
  elections.forEach(function (e) {
    var pts = (e.path || []).filter(function (p) { return isNum(p.v) && isNum(p.k); });
    if (pts.length < 2) { return; }
    var d = pts.map(function (p, j) {
      return (j === 0 ? "M" : "L") + X(p.k).toFixed(1) + "," + Y(p.v).toFixed(1);
    }).join(" ");
    var path = el("path", { d: d, "class": "path-line" }, svg);
    el("title", { text: (e.id || "?") + " midterm path (rebased 100 at election month)" }, path);
  });

  /* bold median path: per-k median across elections */
  var medPts = [];
  for (var k = K0; k <= K1; k++) {
    var vs = [];
    elections.forEach(function (e) {
      (e.path || []).forEach(function (p) {
        if (p.k === k && isNum(p.v)) { vs.push(p.v); }
      });
    });
    if (!vs.length) { continue; }
    vs.sort(function (a, b) { return a - b; });
    var mid = vs.length % 2 ? vs[(vs.length - 1) / 2] : (vs[vs.length / 2 - 1] + vs[vs.length / 2]) / 2;
    medPts.push({ k: k, v: mid });
  }
  if (medPts.length > 1) {
    var md = medPts.map(function (p, j) {
      return (j === 0 ? "M" : "L") + X(p.k).toFixed(1) + "," + Y(p.v).toFixed(1);
    }).join(" ");
    var mp = el("path", { d: md, "class": "median-line" }, svg);
    el("title", { text: "Median path across all midterms" }, mp);
  }

  /* dots at each path's pre-peak and post-peak (matched by month string) */
  elections.forEach(function (e) {
    var byM = {};
    (e.path || []).forEach(function (p) { byM[p.m] = p; });
    var preM = e.swingA && e.swingA.peak;
    var postM = e.swingB && e.swingB.peak;
    if (preM && byM[preM] && isNum(byM[preM].v)) {
      var c1 = el("circle", { cx: X(byM[preM].k), cy: Y(byM[preM].v), r: 3.5, "class": "pre-dot" }, svg);
      el("title", { text: (e.id || "?") + " pre-peak " + preM }, c1);
    }
    if (postM && byM[postM] && isNum(byM[postM].v)) {
      var c2 = el("circle", { cx: X(byM[postM].k), cy: Y(byM[postM].v), r: 3.5, "class": "post-dot" }, svg);
      el("title", { text: (e.id || "?") + " post-peak " + postM }, c2);
    }
  });

  el("line", { x1: L, y1: H - B, x2: W - R, y2: H - B, "class": "axis" }, svg);
}

/* ---------- (3) scatter: x = fear depth (magnitude), y = relief height ---------- */
function drawScatter(svg, elections) {
  var W = 720, H = 420, L = 52, R = 14, T = 14, B = 40;
  svg.innerHTML = "";
  var rows = elections.filter(function (e) {
    return e.swingA && isNum(e.swingA.depth_pct) && e.swingB && isNum(e.swingB.height_pct);
  });
  if (!rows.length) {
    el("text", { x: 20, y: 30, text: "No fear/relief pairs." }, svg);
    return;
  }
  var xs = rows.map(function (e) { return Math.abs(e.swingA.depth_pct); });
  var ys = rows.map(function (e) { return e.swingB.height_pct; });
  var maxX = Math.max.apply(null, xs.concat([1]));
  var maxY = Math.max.apply(null, ys.concat([1]));
  var top = Math.max(maxX, maxY) * 1.08;
  function X(v) { return L + v / top * (W - L - R); }
  function Y(v) { return (T + (H - T - B)) - v / top * (H - T - B); }

  for (var i = 0; i <= 4; i++) {
    var g = top * i / 4;
    el("line", { x1: L, y1: Y(g), x2: W - R, y2: Y(g), "class": "grid" }, svg);
    el("text", { x: 6, y: Y(g) + 4, text: g.toFixed(0) + "%" }, svg);
    el("line", { x1: X(g), y1: T, x2: X(g), y2: H - B, "class": "grid" }, svg);
    el("text", { x: X(g) - 8, y: H - 22, text: g.toFixed(0) + "%" }, svg);
  }
  /* diagonal B/A = 1 */
  el("line", { x1: X(0), y1: Y(0), x2: X(top), y2: Y(top), "class": "diag" }, svg);
  el("text", { x: X(top) - 52, y: Y(top) - 8, text: "B/A = 1" }, svg);
  el("text", { x: L, y: H - 6, text: "Fear depth, % (drawdown magnitude) →" }, svg);

  rows.forEach(function (e) {
    var x = Math.abs(e.swingA.depth_pct);
    var y = e.swingB.height_pct;
    var stance = (e.macro && e.macro.fed_stance) || "unknown";
    var fill = stanceColor(stance);
    var attrs = { cx: X(x), cy: Y(y), r: 6 };
    if (fill) { attrs.fill = fill; }
    else { attrs.fill = "#ffffff"; attrs.stroke = "#1a1a1a"; attrs["stroke-width"] = 2; }
    var c = el("circle", attrs, svg);
    var ba = isNum(e.ba_ratio) ? ", B/A " + e.ba_ratio.toFixed(2) : "";
    el("title", {
      text: e.id + ": fear " + Math.abs(e.swingA.depth_pct).toFixed(2) +
        "%, relief +" + e.swingB.height_pct.toFixed(2) + "%" + ba + ", Fed " + stance
    }, c);
  });
  el("line", { x1: L, y1: H - B, x2: W - R, y2: H - B, "class": "axis" }, svg);
  el("line", { x1: L, y1: T, x2: L, y2: H - B, "class": "axis" }, svg);
}

/* ---------- (4) stats strip ---------- */
function renderStats(box, stats) {
  if (!stats) { box.innerHTML = "<p>No summary statistics.</p>"; return; }
  function cell(label, html) {
    return '<div class="stat"><div class="k">' + esc(label) + '</div><div class="v">' + html + "</div></div>";
  }
  var out = [];
  out.push(cell("Midterms", isNum(stats.n) ? String(stats.n) : dash("No count in stats")));
  out.push(cell("Bottomed ±2m", fmtPct1(stats.hit_rate_2m) !== null ? esc(fmtPct1(stats.hit_rate_2m)) : dash("No hit-rate in stats")));
  out.push(cell("Bottomed ±4w (wk)", (stats.weekly && fmtPct1(stats.weekly.hit_4w) !== null) ? esc(fmtPct1(stats.weekly.hit_4w) + " · n=" + stats.weekly.n) : dash("Weekly bars start 1970")));
  out.push(cell("Bottomed ±8w (wk)", (stats.weekly && fmtPct1(stats.weekly.hit_8w) !== null) ? esc(fmtPct1(stats.weekly.hit_8w) + " · n=" + stats.weekly.n) : dash("Weekly bars start 1970")));
  out.push(cell("Median fear", isNum(stats.median_depth) ? esc(stats.median_depth.toFixed(2) + "%") : dash("No median depth in stats")));
  out.push(cell("Median relief", isNum(stats.median_height) ? esc("+" + stats.median_height.toFixed(2) + "%") : dash("No median height in stats")));
  out.push(cell("Median B/A", isNum(stats.median_ba) ? esc(stats.median_ba.toFixed(2) + "x") : dash("Needs both fear and relief legs")));
  out.push(cell("Relief beats fear", fmtPct1(stats.share_relief_beats_fear) !== null ? esc(fmtPct1(stats.share_relief_beats_fear)) : dash("No share in stats")));
  out.push(cell("Med B/A hiking", isNum(stats.median_ba_hiking) ? esc(stats.median_ba_hiking.toFixed(2) + "x") : dash("No hiking subsample")));
  out.push(cell("Med B/A cutting", isNum(stats.median_ba_cutting) ? esc(stats.median_ba_cutting.toFixed(2) + "x") : dash("No cutting subsample")));
  box.innerHTML = out.join("");
}

/* ---------- (5) sortable table ---------- */
var COLS = [
  { key: "id", label: "Year", type: "str",
    get: function (e) { return e.id; }, title: function () { return "Election year"; } },
  { key: "president", label: "President", type: "str",
    get: function (e) { return e.president; }, title: function () { return "Sitting president"; } },
  { key: "party", label: "Party", type: "str",
    get: function (e) { return e.party; }, title: function () { return "President's party"; } },
  { key: "term", label: "Term", type: "num",
    get: function (e) { return e.term; }, title: function () { return "Presidential term number"; } },
  { key: "divided_after", label: "Divided?", type: "str",
    get: function (e) { return e.divided_after === true ? "Yes" : e.divided_after === false ? "No" : null; },
    title: function () { return "Divided government after the election"; } },
  { key: "recession", label: "Recession?", type: "str",
    get: function (e) { return e.recession === true ? "Yes" : e.recession === false ? "No" : null; },
    title: function () { return "NBER recession around election month"; } },
  { key: "depth", label: "Fear %", type: "num",
    get: function (e) { return e.swingA ? e.swingA.depth_pct : null; },
    title: function (e) { return e.swingA_note || "Move under 0.5% in window — not counted as a swing"; } },
  { key: "height", label: "Relief %", type: "num",
    get: function (e) { return e.swingB ? e.swingB.height_pct : null; },
    title: function (e) { return e.swingB_note || "Move under 0.5% in window — not counted as a swing"; } },
  { key: "ba", label: "B/A", type: "num",
    get: function (e) { return e.ba_ratio; }, title: function () { return "Relief/fear ratio — needs both legs"; } },
  { key: "fed_rate", label: "Fed %", type: "num",
    get: function (e) { return e.macro ? e.macro.fed_rate : null; },
    title: function (e) { return (e.macro_note || "No FRED value") + " — Fed funds rate"; } },
  { key: "stance", label: "Stance", type: "str",
    get: function (e) { return e.macro ? e.macro.fed_stance : null; },
    title: function (e) { return e.macro_note || "Fed hiking/cutting/flat/unknown"; } },
  { key: "cpi", label: "CPI %", type: "num",
    get: function (e) { return e.macro ? e.macro.cpi_yoy : null; },
    title: function (e) { return (e.macro_note || "No FRED value") + " — CPI year on year"; } },
  { key: "unrate", label: "Unrate %", type: "num",
    get: function (e) { return e.macro ? e.macro.unrate : null; },
    title: function (e) { return (e.macro_note || "No FRED value") + " — unemployment rate"; } },
  { key: "unrate_chg", label: "Un Δ6m", type: "num",
    get: function (e) { return e.macro ? e.macro.unrate_chg6m : null; },
    title: function (e) { return (e.macro_note || "No FRED value") + " — unemployment change, 6 months"; } },
  { key: "gs10", label: "10Y %", type: "num",
    get: function (e) { return e.macro ? e.macro.gs10 : null; },
    title: function (e) { return (e.macro_note || "No FRED value") + " — 10-year Treasury yield"; } },
  { key: "gs10_chg", label: "10Y Δ6m", type: "num",
    get: function (e) { return e.macro ? e.macro.gs10_chg6m : null; },
    title: function (e) { return (e.macro_note || "No FRED value") + " — 10-year change, 6 months"; } },
  { key: "cape", label: "CAPE", type: "num",
    get: function (e) {
      if (e.macro && isNum(e.macro.cape_at_prepeak)) { return e.macro.cape_at_prepeak; }
      if (e.swingA && isNum(e.swingA.cape_at_prepeak)) { return e.swingA.cape_at_prepeak; }
      return null;
    }, title: function () { return "Shiller CAPE at the pre-peak"; } },
  { key: "note", label: "Note", type: "str",
    get: function (e) { return e.note || e.macro_note || null; },
    title: function () { return "Election / macro note"; } }
];

var sortState = { key: "id", dir: 1 };

function cellHtml(e, col) {
  var v = col.get(e);
  if (v === null || v === undefined || v === "") { return dash(col.title(e)); }
  var t = col.title(e);
  if (col.type === "num" && typeof v === "number") {
    var s;
    if (col.key === "depth" || col.key === "height" || col.key === "cpi" ||
        col.key === "fed_rate" || col.key === "gs10" || col.key === "unrate" ||
        col.key === "unrate_chg" || col.key === "gs10_chg") {
      s = (v > 0 && (col.key === "height") ? "+" : "") + v.toFixed(2);
    } else if (col.key === "ba" || col.key === "cape" || col.key === "term") {
      s = col.key === "term" ? String(v) : v.toFixed(2);
    } else { s = String(v); }
    return '<span title="' + esc(t) + '">' + esc(s) + "</span>";
  }
  return '<span title="' + esc(t) + '">' + esc(String(v)) + "</span>";
}

function renderTable(elections) {
  var head = document.getElementById("etable-head");
  var body = document.getElementById("etable-body");
  head.innerHTML = "";
  COLS.forEach(function (col) {
    var th = document.createElement("th");
    var arrow = sortState.key === col.key ? (sortState.dir === 1 ? " ▲" : " ▼") : "";
    th.innerHTML = esc(col.label) + '<span class="arrow">' + esc(arrow) + "</span>";
    th.setAttribute("aria-sort",
      sortState.key === col.key ? (sortState.dir === 1 ? "ascending" : "descending") : "none");
    th.title = "Sort by " + col.label;
    th.addEventListener("click", function () {
      if (sortState.key === col.key) { sortState.dir = -sortState.dir; }
      else { sortState.key = col.key; sortState.dir = 1; }
      renderTable(elections);
    });
    head.appendChild(th);
  });
  var col = COLS.filter(function (c) { return c.key === sortState.key; })[0] || COLS[0];
  var rows = elections.slice().sort(function (a, b) {
    var va = col.get(a), vb = col.get(b);
    var na = (va === null || va === undefined || va === "");
    var nb = (vb === null || vb === undefined || vb === "");
    if (na && nb) { return 0; }
    if (na) { return 1; }
    if (nb) { return -1; }
    var cmp;
    if (col.type === "num") { cmp = va - vb; }
    else { cmp = String(va).localeCompare(String(vb)); }
    return cmp * sortState.dir;
  });
  body.innerHTML = "";
  rows.forEach(function (e) {
    var tr = document.createElement("tr");
    tr.innerHTML = COLS.map(function (c) {
      return "<td>" + cellHtml(e, c) + "</td>";
    }).join("");
    body.appendChild(tr);
  });
}

/* ---------- (6) live panel ---------- */
function renderLive(box, live) {
  if (!live) { box.innerHTML = "<p>No live data.</p>"; return; }
  function big(label, value, title) {
    return '<div><div class="lbl">' + esc(label) + '</div><div class="big" title="' +
      esc(title || label) + '">' + value + "</div></div>";
  }
  var spx = isNum(live.spx) ? esc(live.spx.toLocaleString("en-US", { maximumFractionDigits: 2 })) : dash("No S&P quote in feed");
  var days = isNum(live.days_to) ? esc(String(live.days_to)) : dash("No countdown in feed");
  var next = live.next_election ? esc(live.next_election) : dash("No next election in feed");
  var asof = live.asof ? esc(live.asof) : dash("No quote date in feed");
  box.innerHTML =
    big("S&P 500", spx, "S&P 500 as of " + (live.asof || "unknown")) +
    big("As of", asof, "Quote date") +
    big("Next midterm", next, "Next midterm election") +
    big("Days to go", days, "Days to " + (live.next_election || "next midterm"));
}

/* ---------- boot ---------- */
function renderAll(data) {
  var elections = data.elections || [];
  var stats = data.stats, live = data.live;
  document.getElementById("updated").textContent =
    "Data updated " + (data.updated || "unknown") + " · " + elections.length + " midterms since 1934.";
  document.getElementById("verdict").textContent = composeVerdict(stats);
  drawOverlay(document.getElementById("overlay"), elections);
  drawScatter(document.getElementById("scatter"), elections);
  renderStats(document.getElementById("stats"), stats);
  renderTable(elections);
  renderLive(document.getElementById("live"), live);
  document.getElementById("method").textContent = data.method || "No methodology provided.";
}

fetch(DATA_URL).then(function (r) {
  if (!r.ok) { throw new Error("HTTP " + r.status); }
  return r.json();
}).then(renderAll).catch(function (err) {
  ["verdict", "method"].forEach(function (id) {
    document.getElementById(id).textContent = "Could not load midterms.json: " + err.message;
  });
  var live = document.getElementById("live");
  if (live) { live.innerHTML = '<p class="error">Could not load midterms.json.</p>'; }
});

/* Export pure helpers for node testing (harmless in browser). */
if (typeof module !== "undefined" && module.exports) {
  module.exports = { composeVerdict: composeVerdict, asPct: asPct, stanceColor: stanceColor };
}
