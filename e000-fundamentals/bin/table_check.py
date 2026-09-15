#!/usr/bin/env python3
"""table_check.py — TABLE_FIRST fast triage for any p4 experiment.

Usage: python3 table_check.py <experiment_dir> [--served <root.html>]

Offline, seconds, few tokens. Prints PASS/FAIL lines, exits nonzero on FAIL.
New sessions run this FIRST, before reading code.

Checks (see e000-fundamentals/TABLE_FIRST.md):
  T1 NO_TABLE    : served HTML has >=1 data <tr> outside <script>
  T2 COUNTER     : served HTML shows a total-rows counter
  T3 PAGINATION  : served HTML has pagination markers
  T4 TEXT_WALL   : more numbers inside <table> than outside it
  T5 STALE_MASK  : pulse/badge must reflect OLDEST through-date, not newest
Plus an info line: rows=<n> cols=<m> (growth at a glance).
  T6 COUNT_MISMATCH : embedded total vs rows differ without 'N of M'.

Tier 2 UX gaps (see e000-fundamentals/TABLE_UX.md) print as WARN and never
block: W1 PILL_CONTRAST, W2 COLUMN_LAYOUT, W3 NO_SORT_HEADERS,
W4 NO_COLUMN_FILTERS, W5 NO_PAGE_SIZE, W6 NO_SAVED_VIEWS.
"""
import csv
import json
import os
import re
import sys

FAIL = []
WARN = []
INFO = []


def fail(code, msg):
    FAIL.append(f"FAIL {code}: {msg}")


def warn(code, msg):
    WARN.append(f"WARN {code}: {msg}")


def _lum(hex6):
    c = [int(hex6[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contrast(fg, bg):
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _hex3to6(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return h if re.fullmatch(r"[0-9a-fA-F]{6}", h or "") else None


def info(msg):
    INFO.append(msg)


def strip_scripts(html):
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.S | re.I)
    return html


def main():
    exp = sys.argv[1] if len(sys.argv) > 1 else "."
    served = None
    if "--served" in sys.argv:
        served = sys.argv[sys.argv.index("--served") + 1]
    out = os.path.join(exp, "output")
    root_html = served or os.path.join(out, "index.html")
    try:
        html = open(root_html).read()
    except Exception as e:
        print(f"FAIL NO_FILE: cannot read {root_html} ({e})")
        return 2
    body = strip_scripts(html)

    # T1: real data rows (outside <script>; header row excluded)
    trs = len(re.findall(r"<tr[\s>]", body, re.I))
    data_rows = max(trs - 1, 0)  # minus header
    info(f"served_rows={data_rows} (from {root_html})")
    if data_rows < 1:
        fail("NO_TABLE", "served HTML has 0 data rows outside <script> "
             "(empty <table>, JS-only render)")

    # Dataset size (growth at a glance)
    n, cols = None, None
    mj = os.path.join(out, "multiples.json")
    mc = os.path.join(out, "multiples.csv")
    if os.path.exists(mj):
        try:
            d = json.load(open(mj))
            n = len(d.get("protocols", []))
        except Exception:
            pass
    if os.path.exists(mc):
        try:
            with open(mc) as f:
                cols = len(next(csv.reader(f)))
        except Exception:
            pass
    if n is not None:
        info(f"dataset rows={n}" + (f" cols={cols}" if cols else ""))

    # T2: counter (total visible somewhere)
    counter_pat = re.compile(
        r"(\d+\s*(rows|coins|protocols))|(total\b.{0,20}\d+)|"
        r"(page\s+1\s*/\s*\d+)", re.I)
    if not counter_pat.search(body):
        fail("NO_COUNTER", "no total-rows counter visible "
             "(`N rows/coins`, `total`, or `page 1/N`)")
    else:
        info("counter=found")

    # T3: pagination markers
    pag_pat = re.compile(
        r"(pagination)|(per-?page)|(page\s+\d+)|(next|prev)|"
        r"(\b\d+\s*/\s*page)", re.I)
    if not pag_pat.search(body):
        fail("NO_PAGINATION", "no pagination markers "
             "(page 1/N, next/prev, per-page). Dump-all is forbidden on mobile")
    else:
        info("pagination=found")

    # T4: text-wall — numbers inside <table> must beat numbers outside it
    tables = re.findall(r"<table.*?</table>", body, flags=re.S | re.I)
    in_nums = sum(len(re.findall(r"\d+\.?\d*", t)) for t in tables)
    out_nums = len(re.findall(r"\d+\.?\d*", body)) - in_nums
    info(f"numbers_in_tables={in_nums} numbers_outside={out_nums}")
    if out_nums > in_nums:
        fail("TEXT_WALL", f"{out_nums} numbers outside tables vs "
             f"{in_nums} inside — move facts into labeled columns")

    # T5: stale-mask — pulse must use OLDEST through-date
    if n and os.path.exists(mj):
        try:
            d = json.load(open(mj))
            thrus = sorted(p.get("data_through") for p in d["protocols"]
                           if p.get("data_through"))
            if thrus:
                lo, hi = thrus[0], thrus[-1]
                info(f"through oldest={lo} newest={hi}")
                m = re.search(r"data (?:through|mixed)\s+([0-9\-/]+)"
                              r"(?:.{0,5}([0-9\-/]+))?", body)
                if m and lo != hi and lo not in body:
                    fail("STALE_MASK", f"page claims {m.group(0)!r} "
                         f"but oldest row is {lo} (newest {hi})")
        except Exception:
            pass

    # T6: honest count — embedded total vs embedded rows must match,
    # or the page says "N of M" (never show 500 while claiming 653)
    for m in re.findall(r'<script type="application/json" id="tl-data-.*?">(.*?)</script>',
                         html, flags=re.S):
        try:
            jd = json.loads(m)
        except Exception:
            continue
        t, rs = jd.get("total"), jd.get("rows") or []
        if isinstance(t, int) and t != len(rs):
            if f"{len(rs)} of {t}" not in body:
                fail("COUNT_MISMATCH", f"table embeds {len(rs)} rows but "
                     f"claims total {t} without saying 'N of M'")
            else:
                info(f"count honest: {len(rs)} of {t}")

    # T4b: mixed cells — CSV cells mixing number+words (spot check)
    if os.path.exists(mc):
        try:
            with open(mc) as f:
                rows = list(csv.DictReader(f))
            mixed = 0
            for r in rows[:5]:
                for v in (r or {}).values():
                    if isinstance(v, str) and re.search(r"\d", v) and \
                       re.search(r"(median|getting|thru|x\s)", v):
                        mixed += 1
            if mixed:
                fail("MIXED_CELL", f"{mixed} CSV cells mix number+words "
                     "(split: one fact per numeric column)")
        except Exception:
            pass

    # ---- Tier 2 UX gaps (WARN only, never block) ----
    styles = " ".join(re.findall(r"<style.*?>(.*?)</style>", html,
                                   flags=re.S | re.I))
    pills = set(re.findall(r"class=\"[^\"]*\b(thin|badge|stale|pill)\b",
                           body + html))
    for pill in sorted(pills):
        base = re.findall(rf"\.{pill}\s*\{{([^}}]*)}}", styles)
        dark = re.findall(rf"html\.dark\s+\.{pill}\s*\{{([^}}]*)}}",
                          styles)
        decl = " ".join(base)
        bg = re.search(r"background\s*:\s*(#[0-9a-fA-F]{3,6})", decl)
        fg = re.search(r"(?<!-)color\s*:\s*(#[0-9a-fA-F]{3,6})", decl)
        if bg and not fg:
            warn("PILL_CONTRAST", f".{pill} sets background {bg.group(1)} "
                 "but inherits text color — unreadable in dark mode. "
                 "Declare color + an html.dark variant.")
        elif bg and fg:
            b6, f6 = _hex3to6(bg.group(1)), _hex3to6(fg.group(1))
            if b6 and f6:
                r = _contrast(f6, b6)
                info(f"pill .{pill} contrast={r:.1f}")
                if r < 4.5:
                    warn("PILL_CONTRAST", f".{pill} contrast {r:.1f} < 4.5 "
                         f"({fg.group(1)} on {bg.group(1)})")
        if bg and not fg and base and not dark:
            warn("PILL_CONTRAST", f".{pill} has no html.dark variant — "
                 "phone in dark mode is the test.")
    if not re.search(r"(simple.*full|full.*simple|density|column.*(hide|show|toggle)|" 
                       r"transpose|card view|vertical layout)", body, re.I):
        warn("COLUMN_LAYOUT", "user cannot configure columns "
             "(show/hide, order, density, vertical cards). "
             "Fixed wide tables cut columns on narrow phones.")
    else:
        info("column_control=found")
    if not re.search(r"<th[^>]*(onclick|data-sort)|sort.*<th|<th.*sort", body,
                       re.I):
        warn("NO_SORT_HEADERS", "headers are not tappable for sorting. "
             "Tap header = sort is one tap vs finding another control.")
    if not re.search(r"<thead>.*?(<input|<select|data-filter)", body,
                       re.S | re.I):
        warn("NO_COLUMN_FILTERS", "no filters inside column headers. "
             "Filters live where the values are, not in a far toolbar.")
    if not re.search(r"<select", body, re.I):
        warn("NO_PAGE_SIZE", "no page-size selector (10/25/50). "
             "Page size is fixed — the user cannot trade rows vs taps.")
    if not re.search(r"tlApplyView|tl-views|tlShare|presets", body, re.I):
        warn("NO_SAVED_VIEWS", "no saved views / presets / share link. "
             "Users cannot pin a view to the page or share it as a link.")
    else:
        info("views=found")
    for _pm in re.finditer(r'<div id="tl-(views|stats)-([^"]*)"[^>]*>(.*?)</div>',
                            body, flags=re.S):
        _kind, _ns, _panel = _pm.groups()
        _n = len(re.findall(r"tlApplyView|tlSuggestion", _panel))
        if _n > 6 and "tl-more-" not in _panel:
            warn("CHIP_SPAM", f"tl-{_kind}-{_ns}: {_n} chips with no '+N more' "
                 "collapse — chrome buries the table. Budget top-3 + more.")

    for line in INFO:
        print("info " + line)
    if FAIL:
        print("\n".join(FAIL))
    if WARN:
        print("\n".join(WARN))
    if FAIL:
        print(f"TABLE_CHECK: {len(FAIL)} FAIL(s) + {len(WARN)} WARN(s)")
        return 1
    print(f"TABLE_CHECK: PASS + {len(WARN)} WARN(s)"
          if WARN else "TABLE_CHECK: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
