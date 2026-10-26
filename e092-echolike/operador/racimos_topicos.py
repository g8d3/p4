#!/usr/bin/env python3
"""Topic cluster retrospective (code-only, no AI, no network, read-only).

Same rule as operador/alerta_topicos.py (5+ likes on one topic in 24h), but
looks BACKWARD: for each of the last N Bogota days it prints which clusters
would have fired, with the real stored post links. Nothing is invented, sent,
or written — dry-run only. The live alerter (alerta_topicos.py, cron) stays
canonical for actual pings.

Topics are plain keyword/cashtag regexes grounded in Oct 2026 liked texts
(launchpads, AI trading bots, multi-cashtag memecoin chatter).

Usage: python3 operador/racimos_topicos.py [--days 7] [--desde YYYY-MM-DD] [--estado DIR]
  --days: how many Bogota days back (default 7). --desde: first window end
  (default today). --estado: dir holding likes_extension.jsonl + x_items.json
  (default: estado/ next to the script). Reads only, warns when files are missing.
"""
import datetime as dt
import json
import os
import re
import sys

BOG = dt.timezone(dt.timedelta(hours=-5))
VENTANA_H = 24
UMBRAL = 5

TOPICS = {
    "launchpads": [r"launchpad", r"pump\.?fun", r"presale", r"\btge\b", r"\bido\b",
                   r"bonding", r"fair launch", r"\blaunch(?:es|ed|ing)?\b"],
    "ai-trading-bots": [r"ai agent", r"trading bot", r"grok bot", r"inference",
                        r"prompts", r"\bswarm\b", r"hotbot"],
    "memecoins": [r"(\$[A-Z]{2,10}\b.*){2,}", r"\baped\b", r"\bmcap\b",
                  r"market cap", r"dexscreener"],
}


def ts(d):
    for k in ("clicked_at", "recv_at", "visto"):
        v = d.get(k)
        if v:
            try:
                t = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
                return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
            except ValueError:
                continue
    return None


def cargar(estado_dir):
    rows, vistos, faltan = [], set(), []
    jsonl = os.path.join(estado_dir, "likes_extension.jsonl")
    xitems = os.path.join(estado_dir, "x_items.json")
    try:
        f = open(jsonl, encoding="utf-8")
    except OSError:
        f = None
        faltan.append(jsonl)
    if f:
        with f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("kind") != "like":
                    continue
                t = ts(d)
                if not t:
                    continue
                iid = str(d.get("id") or "")
                vistos.add(iid)
                rows.append({"id": iid, "t": t, "text": d.get("text") or "",
                             "url": d.get("url") or "", "handle": d.get("handle") or ""})
    try:
        items = json.load(open(xitems, encoding="utf-8")).get("items") or []
    except Exception:
        items = []
        faltan.append(xitems)
    for d in items:
        if d.get("type") != "like":
            continue
        t = ts(d)
        if not t:
            continue
        iid = str(d.get("id") or "")
        if iid and iid in vistos:
            continue
        vistos.add(iid)
        rows.append({"id": iid, "t": t, "text": d.get("text") or "",
                     "url": d.get("url") or "", "handle": d.get("handle") or ""})
    return rows, faltan


def topic_de(rx, texto):
    return [topic for topic, pats in rx.items()
            if any(p.search(texto or "") for p in pats)]


def main(argv):
    days, desde, estado = 7, None, None
    for i, a in enumerate(argv):
        if a == "--days" and i + 1 < len(argv):
            days = max(1, int(argv[i + 1]))
        if a == "--desde" and i + 1 < len(argv):
            d0 = dt.datetime.strptime(argv[i + 1], "%Y-%m-%d").replace(tzinfo=BOG)
            desde = d0.replace(hour=23, minute=59, second=59, microsecond=0)
        if a == "--estado" and i + 1 < len(argv):
            estado = argv[i + 1]
    if estado is None:
        estado = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "estado")
    rx = {t: [re.compile(p, re.I) for p in pats] for t, pats in TOPICS.items()}
    likes, faltan = cargar(estado)
    for f in faltan:
        print(f"warning: missing {f} (use --estado DIR or run where estado/ exists)", file=sys.stderr)
    if desde is None:
        ahora_bog = dt.datetime.now(dt.timezone.utc).astimezone(BOG)
        desde = ahora_bog.replace(hour=23, minute=59, second=59, microsecond=0)
    fired, out = set(), []
    for back in range(days):
        fin = desde - dt.timedelta(days=back)
        ini = fin - dt.timedelta(hours=VENTANA_H)
        win = [r for r in likes if ini < r["t"] <= fin]
        etiqueta = fin.strftime("%Y-%m-%d")
        grupos = {}
        for r in win:
            for t in topic_de(rx, r["text"]):
                grupos.setdefault(t, []).append(r)
        if not grupos:
            out.append(f"{etiqueta}: {len(win)} likes, no topic hits")
            continue
        for topic in sorted(grupos):
            hits = grupos[topic]
            if len(hits) < UMBRAL:
                out.append(f"{etiqueta}: {topic}: {len(hits)} likes (<{UMBRAL}, no fire)")
                continue
            marca = " (repeat)" if topic in fired else ""
            fired.add(topic)
            seen, links = set(), []
            for h in hits:
                if h["url"] and h["url"] not in seen:
                    seen.add(h["url"])
                    links.append(h["url"])
            dup = len([h for h in hits if h["url"]]) - len(links)
            out.append(f"{etiqueta}: FIRE {topic}: {len(hits)} likes, {len(links)} unique links{marca}")
            for u in links[:10]:
                out.append(f"  - {u}")
            if len(links) > 10:
                out.append(f"  (+{len(links) - 10} more)")
            if len(links) < len(hits):
                out.append(f"  ({len(hits) - len(links)} without stored/duplicate link, not shown)")
    print(f"retrospective: {len(likes)} likes loaded, {days} windows ending {desde.strftime('%Y-%m-%d')}")
    for s in out:
        print(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
