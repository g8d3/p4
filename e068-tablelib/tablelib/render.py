"""tablelib.render — one server-side table renderer for every p4 experiment.

Compliance by construction (TABLE_FIRST + TABLE_UX):
  - real <tr> rows in the served HTML (never JS-only)
  - counter + pagination with per-page select
  - sortable headers (tap = sort), per-column filters in the thead
  - density (simple/full) + cards (vertical) controls, persisted
  - data-l labels on every cell (cards view needs them)
  - contrast-safe pills via table.css (.tl-thin declares bg+fg+both themes)

Column spec: list of dicts with:
  key    : row field name
  label  : header text
  cls    : css class for hide-in-simple rules (host page owns .c-* rules)
  kind   : 'text' | 'num' | 'pill' | 'bar' | 'spark' | 'poly' | 'date'
           pill = number + badge; bar = number + proportional bar
           spark = unicode sparkline from a value list
           poly = SVG polygon mini-chart from a value list
           date = timestamp: cell value is epoch seconds (int/float) or a
             date string (ISO-8601, 'MM/DD HH:MM', ...). Rendered as short
             'MM/DD HH:MM' (UTC, full ISO in title) with data-ts="<epoch>"
             on the <td>; the thead shows from/to range inputs and sorting
             is chronological. date cells also parse standalone relative
             strings ('hace 3 horas', 'en 20 minutos', '3h ago', 'in 2h').
             Text columns whose values mostly parse as dates are
             auto-detected and get the same treatment (display unchanged).
             Packed strings with 2+ dates ('called 5h ago, grades in 2h')
             do NOT parse — split them into atomic columns instead.
  ph     : filter input placeholder (None = no filter for this column)
  fmt    : optional python format, e.g. '{:.2f}' (num/pill/bar only)
  scales : optional {key: (min, max)} for bars; else computed from rows
  suggestions : [{title, detail, state}] insight chips (see stats.py)
"""
import html as _h
import json
import re as _re
import time as _time
from datetime import datetime as _dt, timezone as _tz

BARS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587"


def _isnum(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


# --- date support (kind='date' + auto-detect) ---
# Absolute: epoch s/ms, ISO-8601, 'MM/DD[/YYYY] [HH:MM[:SS]]'.
# Relative (standalone strings only): EN '3h ago' / 'in 2d',
# ES 'hace 3 horas' / 'en 20 minutos' / 'dentro de 2 dias',
# plus ayer/hoy/manana, yesterday/today/tomorrow.
_UNITS = {'s': 1, 'sec': 1, 'secs': 1, 'seg': 1, 'second': 1,
 'seconds': 1, 'segundo': 1, 'segundos': 1, 'm': 60, 'min': 60,
 'mins': 60, 'minute': 60, 'minutes': 60, 'minuto': 60, 'minutos': 60,
 'h': 3600, 'hr': 3600, 'hrs': 3600, 'hour': 3600, 'hours': 3600,
 'hora': 3600, 'horas': 3600, 'd': 86400, 'day': 86400, 'days': 86400,
 'dia': 86400, 'dias': 86400, 'd\u00eda': 86400, 'd\u00edas': 86400,
 'w': 604800, 'wk': 604800, 'wks': 604800, 'week': 604800,
 'weeks': 604800, 'semana': 604800, 'semanas': 604800}
_DAY_WORD = {'ayer': -86400, 'yesterday': -86400, 'hoy': 0, 'today': 0,
 'ma\u00f1ana': 86400, 'manana': 86400, 'tomorrow': 86400}


def _rel_secs(rest):
    """Seconds for '3h 20m' / '2 dias' / 'un minuto'. None if no units."""
    tot, found = 0, False
    for n, u in _re.findall(r'(\d+|un|una)\s*([a-z\u00e1\u00e9\u00ed]+)', rest):
        sec = _UNITS.get(u.rstrip('s') if u not in _UNITS else u, _UNITS.get(u))
        if sec is None:
            return None
        tot += (1 if n in ('un', 'una') else int(n)) * sec
        found = True
    return tot if found else None


def _rel_ts(t, now):
    w = _DAY_WORD.get(t)
    if w is not None:
        return now + w
    m = _re.match(r'^(hace|en|dentro de)\s+(.+)$', t)
    if m:
        secs = _rel_secs(m.group(2))
        if secs is None:
            return None
        return now - secs if m.group(1) == 'hace' else now + secs
    m = _re.match(r'^(.+)\s+ago$', t)
    if m:
        secs = _rel_secs(m.group(1))
        return now - secs if secs is not None else None
    m = _re.match(r'^in\s+(.+)$', t)
    if m:
        secs = _rel_secs(m.group(1))
        return now + secs if secs is not None else None
    return None


def parse_ts(v, now=None):
    """Epoch seconds (float) for a timestamp value, else None.
    Plain small numbers ('12.5', '500+') never parse — only int-like
    values in [1e9, 5e9] count as epoch (ms auto-detected)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        if f >= 1e12:
            f /= 1000.0
        return f if 1e9 <= f <= 5e9 else None
    t = str(v).strip()
    if not t:
        return None
    now = now if now is not None else _time.time()
    if _re.match(r'^\d+(\.\d+)?$', t):
        return parse_ts(float(t), now)
    try:
        d = _dt.fromisoformat(t.replace('Z', '+00:00'))
        if d.tzinfo is None:
            d = d.replace(tzinfo=_tz.utc)
        return d.timestamp()
    except (ValueError, OverflowError):
        pass
    m = _re.match(r'^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?'
                  r'(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$', t)
    if m:
        try:
            mo, da = int(m.group(1)), int(m.group(2))
            yr = m.group(3)
            if yr is None:
                yr = _dt.fromtimestamp(now, _tz.utc).year
            else:
                yr = int(yr) + (2000 if len(yr) == 2 else 0)
            d = _dt(yr, mo, da, int(m.group(4) or 0),
                    int(m.group(5) or 0), int(m.group(6) or 0),
                    tzinfo=_tz.utc)
            return d.timestamp()
        except (ValueError, OverflowError):
            pass
    return _rel_ts(t.lower(), now)


def format_ts(ts):
    """Short UTC display 'MM/DD HH:MM' for an epoch."""
    try:
        d = _dt.fromtimestamp(float(ts), _tz.utc)
        return f'{d.month:02d}/{d.day:02d} {d.hour:02d}:{d.minute:02d}'
    except (TypeError, ValueError, OverflowError, OSError):
        return '\u2014'


def iso_ts(ts):
    try:
        return _dt.fromtimestamp(float(ts), _tz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    except (TypeError, ValueError, OverflowError, OSError):
        return ''


def looks_date(rows, key, sample=50):
    """True when sampled values mostly parse as timestamps."""
    n = hit = 0
    for r in rows:
        v = r.get(key)
        if v in (None, ''):
            continue
        n += 1
        if parse_ts(v) is not None:
            hit += 1
        if n >= sample:
            break
    return n >= 3 and hit / n >= 0.8

def _auto_layout(columns):
    """Default card layout: [title+headline] then field pairs.
    Turns N one-per-row fields into ~N/2 grouped rows."""
    keys = [c["key"] for c in columns]
    if not keys:
        return []
    return [keys[:2]] + [keys[i:i + 2] for i in range(2, len(keys), 2)]


PER_OPTS = (10, 25, 50)
SHOW_N = 3  # visible chips before '+N more' (views + insights budgets)


def _collapse(ns, which, buttons):
    """Top-SHOW_N chips visible, rest behind a '+N more' toggle."""
    vis, hid = buttons[:SHOW_N], buttons[SHOW_N:]
    h = "".join(vis)
    if hid:
        h += (f'<span id="tl-more-{ns}-{which}" style="display:none">'
              + "".join(hid) + "</span>"
              + f' <button onclick="tlMore(\'{ns}\',\'{which}\')">'
              f'+{len(hid)} more</button>')
    return h


def _esc(v):
    return _h.escape(str(v), quote=True)


def render_table(rows, columns, total, page=1, per=10, sort_key=None,
                 sort_dir=1, filters=None, density="simple", view="table",
                 ns="t", presets=None, share=True, suggestions=None,
                 scales=None, row_click=None, row_click_key="token",
                 card_layout=None, bare=False, derived=None):
    filters = filters or {}
    # Date-kind columns (explicit or auto-detected from values) get
    # range inputs + chronological sort + data-ts on cells.
    datecols = {c["key"] for c in columns
                if c.get("kind") == "date" or
                (c.get("kind") == "text" and looks_date(rows, c["key"]))}
    pages = max(1, (total + per - 1) // per)
    page = min(max(page, 1), pages)
    count_txt = (f"{len(rows)} of {total} rows" if total != len(rows)
                 else f"{total} rows")

    ths = []
    frs = []
    for c in columns:
        arr = ""
        if sort_key == c["key"]:
            arr = " &#9650;" if sort_dir == 1 else " &#9660;"
        if not bare and (c.get("kind") in ("text", "num", "pill", "bar", "date")
                         or c["key"] in datecols):
            ths.append(
                f'<th class="{c.get("cls", "")} tl-sort" '
                f'onclick="tlSort(\'{ns}\',\'{c["key"]}\')">'
                f'{_esc(c["label"])}{arr}</th>')

        else:
            ths.append(f'<th class="{c.get("cls", "")}">'
                       f'{_esc(c["label"])}</th>')
        if c.get("nofilter") or c.get("kind") in ("spark", "poly"):
            frs.append(f'<td class="{c.get("cls", "")}"></td>')
        elif c.get("kind") == "date" or c["key"] in datecols:
            f = filters.get(c["key"], {})
            if not isinstance(f, dict):
                f = {}
            frs.append(
                f'<td class="{c.get("cls", "")}"><input type="datetime-local" '
                f'title="from (UTC)" id="tl-f-{ns}-{c["key"]}-lo" '
                f'oninput="tlFilter(\'{ns}\',\'{c["key"]}\',this.value,\'lo\')" '
                f'value="{_esc(f.get("lo", ""))}"> '
                f'<input type="datetime-local" title="to (UTC)" '
                f'id="tl-f-{ns}-{c["key"]}-hi" '
                f'oninput="tlFilter(\'{ns}\',\'{c["key"]}\',this.value,\'hi\')" '
                f'value="{_esc(f.get("hi", ""))}"></td>')
        elif c.get("kind") in ("num", "pill", "bar"):
            f = filters.get(c["key"], {})
            if not isinstance(f, dict):
                f = {}
            frs.append(
                f'<td class="{c.get("cls", "")}"><input '
                f'id="tl-f-{ns}-{c["key"]}-lo" '
                f'oninput="tlFilter(\'{ns}\',\'{c["key"]}\',this.value,\'lo\')" '
                f'placeholder="\u2265 min" value="{_esc(f.get("lo", ""))}"> '
                f'<input id="tl-f-{ns}-{c["key"]}-hi" '
                f'oninput="tlFilter(\'{ns}\',\'{c["key"]}\',this.value,\'hi\')" '
                f'placeholder="\u2264 max" value="{_esc(f.get("hi", ""))}"></td>')
        else:
            fv = _esc(filters.get(c["key"], ""))
            frs.append(
                f'<td class="{c.get("cls", "")}"><input '
                f'id="tl-f-{ns}-{c["key"]}" '
                f'oninput="tlFilter(\'{ns}\',\'{c["key"]}\',this.value)" '
                f'placeholder="{_esc(c.get("ph", c["key"]))}" value="{fv}"></td>')

    scales = dict(scales or {})
    for c in columns:
        if c.get("kind") == "bar" and c["key"] not in scales:
            vs = [float(r[c["key"]]) for r in rows
                  if _isnum(r.get(c["key"]))]
            scales[c["key"]] = (min(vs), max(vs)) if vs else (0, 1)
    suggestions = suggestions or []
    presets = presets or []
    layout = card_layout or _auto_layout(columns)
    page_rows = rows[(page - 1) * per:page * per]
    body = []
    for r in page_rows:
        tr_click = ""
        if row_click:
            tr_click = f' onclick="{row_click}(\'{_esc(r.get(row_click_key, ""))}\')" style="cursor:pointer"'
        tds = []
        for c in columns:
            v = r.get(c["key"])
            cell = _cell(v, c, r, scales)
            _al = "tl-n" if c.get("kind") in ("num", "pill", "bar") else "tl-t"
            _ts = ""
            if c.get("kind") == "date" or c["key"] in datecols:
                _p = parse_ts(v)
                if _p is not None:
                    _ts = f' data-ts="{int(_p)}"'
            tds.append(f'<td data-l="{_esc(c["label"])}" '
                       f'class="{c.get("cls", "")} {_al}"{_ts}>{cell}</td>')
        body.append(f"<tr{tr_click}>" + "".join(tds) + "</tr>")

    opts = "".join(
        f'<option value="{n}"{" selected" if n == per else ""}>'
        f'{n} per page</option>' for n in PER_OPTS)
    _numkeys = [c["key"] for c in columns
                if c.get("kind") in ("num", "pill", "bar")]
    numopts = "".join(
        f'<option value="{c["key"]}">{_esc(c["label"])}</option>'
        for c in columns if c.get("kind") in ("num", "pill", "bar"))
    numopts_b = "".join(
        f'<option value="{k}"{ " selected" if k == (_numkeys[1] if len(_numkeys) > 1 else None) else ""}>'
        f'{_esc(next(c["label"] for c in columns if c["key"] == k))}</option>'
        for k in _numkeys)
    sug_btns = [
        f'<button onclick="tlSuggestion(\'{ns}\',{i})" '
        f'title="{_esc(s.get("detail", ""))}">\U0001f4a1 '
        f'{_esc(s.get("title", ""))}</button>'
        for i, s in enumerate(suggestions)]
    stats = (f'<div id="tl-stats-{ns}" class="cav tl-stats">insights: '
             + _collapse(ns, "sug", sug_btns)
             + f' <button onclick="tlIdeas(\'{ns}\')">\u2728 ideas</button></div>')
    cmp_ = (f'<div id="tl-cmp-{ns}" class="cav tl-cmp">compute: '
            f'<select id="tl-cmp-op-{ns}"><option value="div">A/B</option>'
            f'<option value="sub">A-B</option><option value="add">A+B</option>'
            f'<option value="pct">A% of B</option></select> '
            f'<select id="tl-cmp-a-{ns}">{numopts}</select> '
            f'<select id="tl-cmp-b-{ns}">{numopts_b}</select> '
            f'<button onclick="tlCompute(\'{ns}\')">+ column</button></div>')
    data = {"cols": columns, "rows": rows, "total": total, "per": per,
            "sortKey": sort_key, "sortDir": sort_dir, "layout": layout,
            "presets": presets, "suggestions": suggestions,
            "derived": derived or {},
            "rowClick": ([row_click, row_click_key]
                          if row_click else None)}
    chips = (f'<span id="tl-presets-{ns}">' + _collapse(ns, "pre", [
        f'<button onclick="tlApplyView(\'{ns}\',{i},1)">'
        f'{_esc(v["name"])}</button>' for i, v in enumerate(presets)])
        + "</span>")
    share_btns = (f'<button onclick="tlSaveView(\'{ns}\')">+ save</button>'
                   f'<button onclick="tlShare(\'{ns}\')">share</button>'
                   if share else "")
    views = (f'<div id="tl-views-{ns}" class="cav tl-views">views: '
             f'{chips}<span id="tl-uviews-{ns}"></span>{share_btns}</div>')
    if bare:
        return (f'<div class="twrap"><table id="tl-{ns}"><thead><tr>'
                + "".join(ths) + "</tr></thead><tbody>" + "".join(body)
                + "</tbody></table></div>"
                f'<script type="application/json" id="tl-data-{ns}">'
                f'{json.dumps(data)}</script>')
    return (
        views +
        stats + cmp_ +
        f'<div id="tl-ctl-{ns}" class="cav tl-ctl">density: '
        f'<button onclick="tlDensity(\'{ns}\',\'simple\')">simple</button>'
        f'<button onclick="tlDensity(\'{ns}\',\'full\')">full</button> '
        f'<button onclick="tlCards(\'{ns}\')">cards</button></div>'
        f'<div class="twrap"><table id="tl-{ns}"><thead><tr>'
        + "".join(ths) + "</tr><tr>" + "".join(frs)
        + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
        f'<div id="tl-cards-{ns}" class="tl-cards-div" style="display:none"></div>' 
        f'<div id="tl-pager-{ns}" class="cav">Page <input id="tl-pg-{ns}" '
        f'type="number" value="{page}" min="1" max="{pages}" style="width:3.5em" '
        f'onchange="tlGoto(\'{ns}\',this.value)">/{pages} '
        f'\u00b7 {count_txt} \u00b7 <input id="tl-per-{ns}" type="number" '
        f'value="{per}" min="1" max="1000" style="width:4.5em" '
        f'onchange="tlSetPer(\'{ns}\',this.value)"> per page '
        f'<button onclick="tlPage(\'{ns}\',-1)">\u2190 Prev</button> '
        f'<button onclick="tlPage(\'{ns}\',1)">Next \u2192</button></div>'
        f'<script type="application/json" id="tl-data-{ns}">'
        f'{json.dumps(data)}</script>'
        f'<script>try{{if(window.innerWidth<600&&!localStorage[\'tl-cards\'])'
        f'document.body.classList.add(\'tl-cards\')}}catch(e){{}}</script>')


def _spark(vals):
    vs = [float(x) for x in vals if _isnum(x)]
    if not vs:
        return "\u2014"
    lo, hi = min(vs), max(vs)
    if hi == lo:
        return BARS[3] * len(vs)
    return "".join(BARS[min(int((v - lo) / (hi - lo) * 6), 6)] for v in vs)


def _poly(vals, w=80, h=20):
    vs = [float(x) for x in vals if _isnum(x)]
    if len(vs) < 2:
        return "\u2014"
    lo, hi = min(vs), max(vs)
    rng = (hi - lo) or 1
    pts = " ".join(
        f"{i * w / (len(vs) - 1):.1f},{h - (v - lo) / rng * (h - 2) - 1:.1f}"
        for i, v in enumerate(vs))
    return (f'<svg width="{w}" height="{h}"><polyline points="{pts}" '
            f'fill="none" stroke="currentColor" stroke-width="1.5"/></svg>')


def _cell(v, c, r, scales):
    if v is None:
        return "\u2014"
    if c.get("kind") == "pill":
        pill = r.get(c.get("pill_key", ""), "")
        badge = (f' <span class="tl-thin">thin n={_esc(pill)}</span>'
                 if pill != "" and pill is not None else "")
        num = _fmt_num(v, c)
        return f"{num}{badge}"
    if c.get("kind") == "bar":
        num = _fmt_num(v, c)
        try:
            lo, hi = scales.get(c["key"], (0, 1))
            pct = max(0, min(100, (float(v) - lo) / ((hi - lo) or 1) * 100))
        except (TypeError, ValueError):
            pct = 0
        return (f'<span class="tl-bar"><span style="width:{pct:.0f}%">'
                f'</span></span> {num}')
    if c.get("kind") == "spark":
        return _spark(v) if isinstance(v, (list, tuple)) else _esc(v)
    if c.get("kind") == "poly":
        return _poly(v) if isinstance(v, (list, tuple)) else _esc(v)
    if c.get("kind") == "num":
        return _fmt_num(v, c)
    if c.get("kind") == "date":
        _p = parse_ts(v)
        if _p is None:
            return _esc(v)
        return (f'<span title="{iso_ts(_p)}">{_esc(format_ts(_p))}</span>')
    return _esc(v)


def _fmt_num(v, c):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _esc(v)
    fmt = c.get("fmt")
    if fmt:
        try:
            return _esc(fmt.format(f))
        except Exception:
            pass
    return _esc(f"{f:.2f}".rstrip("0").rstrip("."))
