"""tablelib.stats — dependency-free analytics for any table.

Generic presets, one-tap statistics, and the suggestion feed that powers
the AI hooks. Pure stdlib: runs server-side (SSR chips) and documents the
JSON contract an AI endpoint can fulfil instead of these heuristics.

Suggestion shape (both heuristics and AI return this):
  {"title": str, "detail": str, "state": {...display-view state...}}
`state` uses the same keys as URL-hash views (sortKey, sortDir, filters,
per, density, cards) so every suggestion is one tap away from its view.
"""
import math
import re


def _nums(rows, key):
    out = []
    for r in rows:
        try:
            v = float(r.get(key))
        except (TypeError, ValueError):
            continue
        out.append((r, v))
    return out


def describe(rows, key):
    """min/max/mean/median/stdev/n for one numeric column."""
    vs = sorted(v for _, v in _nums(rows, key))
    n = len(vs)
    if not n:
        return {"n": 0}
    mean = sum(vs) / n
    mid = n // 2
    med = (vs[mid] + vs[~mid]) / 2
    var = sum((v - mean) ** 2 for v in vs) / n
    return {"n": n, "min": vs[0], "max": vs[-1], "mean": mean,
            "median": med, "stdev": math.sqrt(var)}


def corr(rows, ka, kb):
    """Pearson correlation between two numeric columns (-1..1, None if n/a)."""
    a = {id(r): v for r, v in _nums(rows, ka)}
    pairs = [(v, float(r.get(kb))) for r in rows if id(r) in a
             for v in [a[id(r)]] if _isnum(r.get(kb))]
    n = len(pairs)
    if n < 3:
        return None
    ma = sum(p[0] for p in pairs) / n
    mb = sum(p[1] for p in pairs) / n
    sa = math.sqrt(sum((p[0] - ma) ** 2 for p in pairs))
    sb = math.sqrt(sum((p[1] - mb) ** 2 for p in pairs))
    if not sa or not sb:
        return None
    return sum((p[0] - ma) * (p[1] - mb) for p in pairs) / (sa * sb)


def _isnum(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def outliers(rows, key, k=2.0):
    """Rows whose |z-score| > k on one column (pattern detector, offline)."""
    pts = _nums(rows, key)
    n = len(pts)
    if n < 4:
        return []
    mean = sum(v for _, v in pts) / n
    sd = math.sqrt(sum((v - mean) ** 2 for _, v in pts) / n)
    if not sd:
        return []
    return [r for r, v in pts if abs((v - mean) / sd) > k]


def auto_presets(rows, columns, per=10):
    """Generic presets derived from the table itself — no experiment code.

    First numeric column -> 'lowest N' view; every numeric column gets an
    'outliers' view when any exist. All presets are plain view states.
    """
    numcols = [c for c in columns if c.get("kind") in ("num", "pill", "bar")]
    if not numcols:
        return []
    out = [{"name": f"lowest {numcols[0]['label']}",
            "state": {"sortKey": numcols[0]["key"], "sortDir": 1,
                      "per": per, "filters": {}}}]
    ranked = []
    for c in numcols:
        outs = outliers(rows, c["key"])
        if 1 <= len(outs) <= 8:
            ranked.append((len(outs), {"name": f"{c['label']} outliers",
                        "state": {"sortKey": c["key"], "sortDir": -1,
                                  "per": per, "filters": {}}}))
    ranked.sort(key=lambda t: t[0])
    cat_chips = []
    for c in columns:
        if c.get("kind") not in ("text",) or c.get("nofacet"):
            continue
        vals = sorted({str(r.get(c["key"], "")) for r in rows
                       if r.get(c["key"]) not in (None, "")})
        if not (3 <= len(vals) <= 8):
            continue
        if any(re.match(r"^\d{4}-\d{2}-\d{2}", v) for v in vals):
            continue  # dates are not facets
        cat_chips += [{"name": v, "state": {"filters": {c["key"]: v}}}
                      for v in vals]
    out[1:1] = cat_chips
    return out + [r[1] for r in ranked]


def _lineage(key, derived):
    """Ancestor set of a column. `derived` maps column -> source column(s)
    (str or list); pairs whose ancestor sets intersect are skipped — a
    column trivially correlates with what it is computed from."""
    seen, stack, out = {key}, [key], set()
    while stack:
        k = stack.pop()
        for parent in ([derived[k]] if isinstance(derived.get(k), str)
                       else list(derived.get(k) or [])):
            out.add(parent)
            if parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return out


def suggest(rows, columns, limit=6, derived=None):
    """Heuristic insight feed. An AI endpoint may return the same shape
    (see AGENTS.md `/api/suggest` contract) — the GUI cannot tell them apart.
    `derived` maps column -> its source column; pairs sharing lineage are
    skipped (a column trivially correlates with what it is computed from).
    """
    derived = derived or {}
    ouls, cors = [], []
    numcols = [c for c in columns if c.get("kind") in ("num", "pill", "bar")]
    for c in numcols:
        d = describe(rows, c["key"])
        if not d.get("n"):
            continue
        outs = outliers(rows, c["key"])
        if 1 <= len(outs) <= 8:
            names = ", ".join(str(r.get("token", r.get("coin", "?"))) for r in outs[:3])
            plural = "s" if len(outs) != 1 else ""
            ouls.append((len(outs), {
                "title": f"{len(outs)} outlier{plural} in {c['label']}",
                "detail": f"{names} beyond 2 std (mean {d['mean']:.2f})",
                "state": {"sortKey": c["key"], "sortDir": -1,
                          "per": 10, "filters": {},
                          "stats_for": c["key"]}}))
    for i, a in enumerate(numcols):
        for b in numcols[i + 1:]:
            la, lb = _lineage(a["key"], derived), _lineage(b["key"], derived)
            if la & lb or a["key"] in lb or b["key"] in la:
                continue
            r = corr(rows, a["key"], b["key"])
            if r is not None and abs(r) >= 0.7:
                cors.append((abs(r), {
                    "title": f"{a['label']} ~ {b['label']}: {r:+.2f}",
                    "detail": "strong linear link — move together",
                    "state": {"sortKey": a["key"], "sortDir": -1,
                              "per": 10, "filters": {},
                              "stats_for": a["key"]}}))
    ouls.sort(key=lambda t: t[0])
    cors.sort(key=lambda t: -t[0])
    ranked = [x[1] for x in ouls]
    if len(ranked) < limit:
        ranked += [x[1] for x in cors][:limit - len(ranked)]
    return ranked[:limit]
